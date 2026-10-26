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
  test('blu withdrawal, deposit, charge', () {
    final w = parseBluSms('بلو\nبرداشت پول\nماني عزیز، 334,840ریال از حساب شما پرید.\nموجودی: 43,415,184 ریال')!;
    expect((w.type, w.amount, w.balance, w.description), ('expense', 334840, 43415184, 'برداشت پول'));
    final i = parseBluSms('بلو\nواریز پول\nماني عزیز، 52,607,850ریال به حساب شما نشست.\nموجودی: 52,620,024 ریال')!;
    expect((i.type, i.amount, i.balance), ('income', 52607850, 52620024));
    final c = parseBluSms('بلو\nشارژ شدی\n ماني عزیز، 500,000 ریال بابت خرید شارژ از حساب شما پرید.\nموجودی: 4,123,174 ریال')!;
    expect((c.type, c.amount, c.description), ('expense', 500000, 'خرید شارژ'));
  });
  test('blu one-time-password SMS is ignored', () {
    expect(parseBluSms('بلو\nبفرمایید رمز پویا\nخرید\nايرانسل\nمبلغ: 334,840 ریال\nرمز: 284046'), isNull);
  });
}
