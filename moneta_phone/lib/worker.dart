import 'package:workmanager/workmanager.dart';
import 'sms_service.dart';
import 'uploader.dart';

const syncTask = 'moneta-sync';

/// Runs in the background every ~30 min, even when the app is closed.
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, input) async {
    try {
      await SmsService.scanInbox(background: true);
    } catch (_) {}
    try {
      await Uploader.syncPending();
    } catch (_) {}
    return true; // failed? skip. The next run is in 30 min.
  });
}

Future<void> startWorker() async {
  await Workmanager().initialize(callbackDispatcher);
  await Workmanager().registerPeriodicTask(
    syncTask,
    syncTask,
    frequency: const Duration(minutes: 30),
    constraints: Constraints(networkType: NetworkType.connected),
  );
}
