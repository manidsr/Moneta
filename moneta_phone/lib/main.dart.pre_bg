import 'package:flutter/material.dart';
import 'sms_service.dart';
import 'store.dart';
import 'uploader.dart';

void main() => runApp(const MaterialApp(
    title: 'Moneta', debugShowCheckedModeBanner: false, home: Home()));

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  final url = TextEditingController(), token = TextEditingController(), sender = TextEditingController();
  bool toman = true, raw = false, busy = false;
  int pending = 0, sent = 0;
  String status = '';
  List<Tx> recent = [];

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final s = await Settings.load();
    url.text = s.scriptUrl;
    token.text = s.token;
    sender.text = s.senderSuffix;
    toman = s.rialToToman;
    raw = s.sendRaw;
    try {
      SmsService.listen(_refresh);
    } catch (_) {}
    await _refresh();
  }

  Future<void> _refresh() async {
    final p = await Store.count(sent: false), s = await Store.count(sent: true), r = await Store.recent();
    if (mounted) setState(() { pending = p; sent = s; recent = r; });
  }

  Future<void> _saveSettings() async {
    await Settings(url.text, token.text, sender.text, toman, raw).save();
    setState(() => status = 'Settings saved');
  }

  Future<void> _scanAndSync() async {
    await _saveSettings();
    setState(() { busy = true; status = 'Reading messages...'; });
    try {
      final added = await SmsService.scanInbox();
      setState(() => status = 'Found $added new message(s). Uploading...');
      final err = await Uploader.syncPending();
      status = err ?? 'Done. $added new message(s) queued and uploaded.';
    } catch (e) {
      status = '$e';
    }
    setState(() => busy = false);
    await _refresh();
  }

  String _fmt(int n) => n.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Moneta phone')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          Text('Waiting to upload: $pending    Uploaded: $sent', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          FilledButton.icon(
              onPressed: busy ? null : _scanAndSync,
              icon: const Icon(Icons.sync),
              label: Text(busy ? 'Working...' : 'Scan inbox & sync')),
          if (status.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(status)),
          ExpansionTile(title: const Text('Settings'), children: [
            TextField(controller: url, decoration: const InputDecoration(labelText: 'Apps Script web app URL')),
            TextField(controller: token, decoration: const InputDecoration(labelText: 'Secret token')),
            TextField(controller: sender, decoration: const InputDecoration(labelText: 'Sender(s) (end of number, comma separated)')),
            SwitchListTile(title: const Text('Convert rial to toman (÷10)'), value: toman, onChanged: (v) => setState(() => toman = v)),
            SwitchListTile(title: const Text('Also send original SMS text'), value: raw, onChanged: (v) => setState(() => raw = v)),
            TextButton(onPressed: _saveSettings, child: const Text('Save settings')),
          ]),
          const Divider(),
          for (final t in recent)
            ListTile(
              dense: true,
              leading: Icon(t.type == 'income' ? Icons.south_west : Icons.north_east,
                  color: t.type == 'income' ? Colors.green : Colors.red),
              title: Text('${t.type == 'income' ? '+' : '-'}${_fmt(t.amount)}  ${t.description}'),
              subtitle: Text(DateTime.fromMillisecondsSinceEpoch(t.date).toString().substring(0, 16)),
              trailing: Icon(t.sent ? Icons.cloud_done : Icons.cloud_upload_outlined),
            ),
        ]),
      );
}
