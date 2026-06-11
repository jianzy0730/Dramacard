package com.dramacard.client

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.dramacard.client.ui.DramaCardApp
import com.dramacard.client.ui.theme.DramaCardTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            DramaCardTheme {
                DramaCardApp()
            }
        }
    }
}
