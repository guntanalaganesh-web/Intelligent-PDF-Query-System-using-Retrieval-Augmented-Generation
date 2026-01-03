package com.pdfrag.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            PDFRAGTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF0F172A)
                ) {
                    PDFRAGApp()
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PDFRAGApp() {
    val navController = rememberNavController()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "PDF Intelligence",
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1E293B)
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = Color(0xFF1E293B)
            ) {
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                    label = { Text("Documents") },
                    selected = true,
                    onClick = { }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Add, contentDescription = "Upload") },
                    label = { Text("Upload") },
                    selected = false,
                    onClick = { }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    selected = false,
                    onClick = { }
                )
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "documents",
            modifier = Modifier.padding(padding)
        ) {
            composable("documents") { DocumentsScreen() }
            composable("chat/{documentId}") { ChatScreen() }
        }
    }
}

@Composable
fun DocumentsScreen() {
    val documents = remember {
        listOf(
            Document("1", "Annual Report 2024.pdf", 45, "completed"),
            Document("2", "Technical Specs.pdf", 23, "completed"),
            Document("3", "Research Paper.pdf", 12, "processing")
        )
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
            .padding(16.dp)
    ) {
        Text(
            "Your Documents",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White,
            modifier = Modifier.padding(bottom = 16.dp)
        )
        
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(documents) { doc ->
                DocumentCard(doc)
            }
        }
    }
}

@Composable
fun DocumentCard(document: Document) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFF1E293B)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .background(
                        Color(0xFFEF4444).copy(alpha = 0.2f),
                        RoundedCornerShape(8.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Description,
                    contentDescription = null,
                    tint = Color(0xFFF87171)
                )
            }
            
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 12.dp)
            ) {
                Text(
                    document.filename,
                    color = Color.White,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    "${document.pageCount} pages",
                    color = Color(0xFF94A3B8),
                    fontSize = 14.sp
                )
            }
            
            StatusBadge(document.status)
        }
    }
}

@Composable
fun StatusBadge(status: String) {
    val (bgColor, textColor) = when (status) {
        "completed" -> Color(0xFF22C55E).copy(alpha = 0.2f) to Color(0xFF4ADE80)
        "processing" -> Color(0xFFEAB308).copy(alpha = 0.2f) to Color(0xFFFACC15)
        else -> Color(0xFFEF4444).copy(alpha = 0.2f) to Color(0xFFF87171)
    }
    
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = bgColor
    ) {
        Text(
            status,
            color = textColor,
            fontSize = 12.sp,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun ChatScreen() {
    var query by remember { mutableStateOf("") }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
    ) {
        // Messages area
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                AssistantMessage("Hello! Ask me anything about your document.")
            }
        }
        
        // Input area
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1E293B))
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                placeholder = { Text("Ask a question...") },
                modifier = Modifier.weight(1f),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF3B82F6),
                    unfocusedBorderColor = Color(0xFF334155)
                )
            )
            
            IconButton(
                onClick = { /* Send query */ }
            ) {
                Icon(
                    Icons.Default.Send,
                    contentDescription = "Send",
                    tint = Color(0xFF3B82F6)
                )
            }
        }
    }
}

@Composable
fun AssistantMessage(content: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(
                    Brush.linearGradient(
                        colors = listOf(Color(0xFF3B82F6), Color(0xFF06B6D4))
                    ),
                    RoundedCornerShape(16.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.Default.AutoAwesome,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(16.dp)
            )
        }
        
        Card(
            modifier = Modifier
                .padding(start = 8.dp)
                .weight(1f),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xFF1E293B)
            )
        ) {
            Text(
                content,
                color = Color(0xFFE2E8F0),
                modifier = Modifier.padding(12.dp)
            )
        }
    }
}

data class Document(
    val id: String,
    val filename: String,
    val pageCount: Int,
    val status: String
)

@Composable
fun PDFRAGTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF3B82F6),
            surface = Color(0xFF1E293B),
            background = Color(0xFF0F172A)
        ),
        content = content
    )
}
