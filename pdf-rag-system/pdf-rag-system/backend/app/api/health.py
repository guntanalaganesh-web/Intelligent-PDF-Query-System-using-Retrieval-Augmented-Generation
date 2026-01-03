"""
Health Check Endpoints - For monitoring and load balancer health checks.
"""

import os
import logging
from datetime import datetime

from flask import Blueprint, jsonify
import psutil

from app import db, cache

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'pdf-rag-api'
    })


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    Used by Kubernetes/ECS for determining if pod can receive traffic.
    """
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        's3': check_s3(),
        'openai': check_openai()
    }
    
    all_healthy = all(c['healthy'] for c in checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'ready' if all_healthy else 'not_ready',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': checks
    }), status_code


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - verifies the application is running.
    Used by Kubernetes/ECS to determine if container should be restarted.
    """
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat(),
        'uptime_seconds': get_uptime()
    })


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Metrics endpoint for monitoring systems.
    Returns system and application metrics.
    """
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        },
        'process': {
            'memory_mb': round(psutil.Process().memory_info().rss / (1024 * 1024), 2),
            'cpu_percent': psutil.Process().cpu_percent(),
            'threads': psutil.Process().num_threads()
        }
    })


def check_database():
    """Check database connectivity."""
    try:
        db.session.execute('SELECT 1')
        return {'healthy': True, 'latency_ms': 0}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {'healthy': False, 'error': str(e)}


def check_cache():
    """Check cache (Redis) connectivity."""
    try:
        cache.set('health_check', 'ok', timeout=10)
        value = cache.get('health_check')
        return {'healthy': value == 'ok', 'latency_ms': 0}
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {'healthy': False, 'error': str(e)}


def check_s3():
    """Check S3 connectivity."""
    try:
        import boto3
        s3 = boto3.client('s3')
        bucket = os.getenv('S3_BUCKET_NAME', 'pdf-rag-documents')
        s3.head_bucket(Bucket=bucket)
        return {'healthy': True}
    except Exception as e:
        logger.warning(f"S3 health check failed: {str(e)}")
        return {'healthy': False, 'error': str(e)}


def check_openai():
    """Check OpenAI API connectivity."""
    try:
        import openai
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            return {'healthy': False, 'error': 'API key not configured'}
        return {'healthy': True}
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {str(e)}")
        return {'healthy': False, 'error': str(e)}


# Track application start time
_start_time = datetime.utcnow()


def get_uptime():
    """Get application uptime in seconds."""
    return (datetime.utcnow() - _start_time).total_seconds()
