package com.example.moneta_phone

import android.content.Intent
import android.net.Uri
import android.os.PowerManager
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "moneta/battery")
            .setMethodCallHandler { call, result ->
                if (call.method == "request") {
                    val pm = getSystemService(POWER_SERVICE) as PowerManager
                    if (!pm.isIgnoringBatteryOptimizations(packageName)) {
                        startActivity(
                            Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                                Uri.parse("package:$packageName"))
                        )
                    }
                    result.success(true)
                } else {
                    result.notImplemented()
                }
            }
    }
}
