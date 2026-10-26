import 'package:flutter_test/flutter_test.dart';
import 'package:moneta_phone/parser.dart';

void main() {
  test('internet purchase', () {
    final p = parseBankSms('بانك ملي ايران\nخريداينترنتي:372,900-\nحساب:22003\nمانده:12,841,836\n0719-08:33')!;
    expect((p.type, p.amount, p.balance, p.account), ('expense', 372900, 12841836, '22003'));
    expect(p.description, 'خریداینترنتی');
  });
  test('withdrawal and income transfer', () {
    final w = parseBankSms('بانك ملي ايران\nبرداشت:2,262,000-\nحساب:22003\nمانده:13,214,736\n0718-20:37')!;
    expect((w.type, w.amount, w.balance), ('expense', 2262000, 13214736));
    final i = parseBankSms('بانك ملي ايران\nانتقال:10,000,000+\nحساب:22003\nمانده:22,816,736\n0718-16:16')!;
    expect((i.type, i.amount, i.description), ('income', 10000000, 'انتقال'));
  });
  test('non-transaction text is ignored', () {
    expect(parseBankSms('کد تایید: 123456'), isNull);
  });
}
