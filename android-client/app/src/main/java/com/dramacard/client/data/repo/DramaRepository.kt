package com.dramacard.client.data.repo

import android.content.Context
import com.dramacard.client.data.model.DramaContent

interface DramaRepository {
    suspend fun loadDramaContent(context: Context): DramaContent
}
