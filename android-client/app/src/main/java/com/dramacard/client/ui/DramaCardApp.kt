package com.dramacard.client.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.dramacard.client.player.PlayerRoute

@Composable
fun DramaCardApp() {
    Surface(modifier = Modifier.fillMaxSize()) {
        PlayerRoute()
    }
}
