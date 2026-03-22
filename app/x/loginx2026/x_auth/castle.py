"""
Castle Token — توكن أمان يُرسل مع كل خطوة تسجيل دخول
"""
import random
import time
import datetime
import base64
import re
import mmh3

from .crypto import (
    n_digit_hex, xor_stream, arr_to_2dig_hex_string, xxtea_encrypt,
    encode_field, encode_optional_index, index_of, bits_to_hex,
    pack_15_16_bits, encode_xxtea_frame, to_byte_array_manual
)


# ============ create4: make_time_token ============
def encode_time_hex(t):
    time_diff = int(t / 1000 - 1535000000)
    arr = [time_diff >> 24, time_diff >> 16, time_diff >> 8, time_diff]
    return arr_to_2dig_hex_string(arr)


def make_time_token(t, random_value):
    random_hex = format(random_value, 'x')
    time_hex = encode_time_hex(t)
    mod_1000_hex = n_digit_hex(t % 1000, 4)
    return (
        xor_stream(time_hex[1:], random_hex)
        + random_hex
        + xor_stream(mod_1000_hex, random_hex)[1:]
        + random_hex
    )


# ============ create5: encode_to_4dig_hex ============
def encode_to_4dig_hex(n):
    value = n << 11 | 258
    return n_digit_hex(value, 4, stop=True)


# ============ create8: encode_3_arrs ============
def float_encode(exp_bits, mant_bits, x):
    if x == 0:
        return 0
    e = 0
    x = abs(x)
    while x >= 2:
        x /= 2
        e += 1
    while x < 1:
        x *= 2
        e -= 1
    e = min(e, (1 << exp_bits) - 1)
    m = 0
    x -= 1
    for _ in range(mant_bits):
        x *= 2
        bit = int(x)
        m = (m << 1) | bit
        x -= bit
    return (e << mant_bits) | m


def encode_mini_float_byte(value):
    if value is None:
        return 0
    value = max(value, 0)
    if value > 15:
        v = min(value, 65536) - 14
        return float_encode(4, 3, v) | 0x80
    else:
        return float_encode(2, 4, value + 1) | 0x40


def encode_array_to_hex(arr):
    return ''.join(map(lambda x: n_digit_hex(encode_mini_float_byte(x), 2), arr))


def arr_to_16bits(arr):
    bits = list(map(lambda x: int(bool(x)), arr[:16]))
    if len(bits) < 16:
        bits += [0] * (16 - len(bits))
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def build_arr1_header(arr1):
    return 6 << 20 | 2 << 16 | (arr_to_16bits(arr1) & 65535)


def int_to_fixed_hex(n):
    max_value = (1 << (8 * 3)) - 1
    n = min(max_value, n)
    return n.to_bytes(3, byteorder='big').hex()


def arr_to_hex_2dig(arr):
    return ''.join(map(lambda x: n_digit_hex(x, 2), arr))


def encode_3_arrs(arr1, arr2, arr3):
    return int_to_fixed_hex(build_arr1_header(arr1)) + encode_array_to_hex(arr2) + arr_to_hex_2dig(arr3) + n_digit_hex(len(arr3), 2)


# ============ func2 ============
def rotate_string(s, n):
    if not s:
        return s
    shift = n % len(s)
    return s[shift:] + s[:shift]


def encode_two_values(n1, n2):
    val = ((n1 * 2) & 0xFFF) << 4 | (n2 % 32 & 0xFF)
    return f'{val:04x}'


def encode_lists(lists):
    nums = [0, 4, 7, 8, 9]
    result = []
    for num, lst in zip(nums, lists):
        encoded = encode_two_values(num, len(lst))
        result.append(encoded)
        result.extend([str(item) for item in lst])
    return ''.join(result)


def xor_with_rotated_key(data, key, key_length, rotate_n_hex):
    key_part = key[:key_length]
    n = int(rotate_n_hex, 16)
    shift = n % len(key_part)
    rotated_key = key_part[shift:] + key_part[:shift]
    return xor_stream(data, rotated_key)


def func2(value, i, cuid):
    time_token = value[0]
    xor1 = time_token + xor_with_rotated_key(
        encode_lists(i[6])
        + n_digit_hex(len(i[2]) // 2, 4, stop=True)
        + value[1]
        + i[8]
        + 'ff',
        time_token,
        4,
        time_token[3],
    )
    return (
        i[4]
        + i[5]
        + '4176526137396248794a53595351486e52706356747a79786574537646657278'
        + cuid
        + xor_with_rotated_key(xor1, cuid, 8, cuid[9])
    )


# ============ func3 ============
def hex_to_int_arr(hex_str):
    arr = []
    for i in range(0, len(hex_str), 2):
        arr.append(int(hex_str[i:i+2], 16))
    return arr


def process1(data):
    key = [1164413191, 3891440048, 218959117, 2746598870]
    enc = xxtea_encrypt(data, key)
    bytes_list = []
    for v in enc:
        v &= 0xFFFFFFFF
        bytes_list.extend([
            v & 0xFF,
            (v >> 8) & 0xFF,
            (v >> 16) & 0xFF,
            (v >> 24) & 0xFF,
        ])
    return len(data), bytes_list


def process2(data):
    return (
        '0d'
        + n_digit_hex(len(data[1]) - data[0], 2)
        + arr_to_2dig_hex_string(data[1])
    )


def func3(data):
    return process2(process1(hex_to_int_arr(data)))


# ============ func4 ============
def hex_to_bin(hex_str):
    return bytes(int(hex_str[i:i + 2], 16) for i in range(0, len(hex_str), 2))


def func4(value, i):
    n = hex_to_bin(i[3] + xor_stream(value + n_digit_hex(len(value), 2), i[3]))
    b64 = base64.b64encode(n).decode()
    return re.sub(r'=+$', '', b64.replace('+', '-').replace('/', '_'))


# ============ Fingerprint Preset ============
def fingerprint_preset(init_time):
    zero = [
        encode_optional_index(0, index_of(['MacIntel', 'Win32', 'iPhone', 'Linux armv8l', 'iPad', 'Linux armv81', 'Linux aarch64', 'Linux x86_64', 'Linux armv7l'], 'Win32'), 'Win32', init_time),
        encode_optional_index(1, index_of(['Google Inc.', 'Apple Computer, Inc.'], 'Google Inc.'), 'Google Inc.', init_time),
        encode_optional_index(2, index_of(['US-US','ES-ES','FR-FR','BR-BR','GB-GB','DE-DE','RU-RU','us-us','gb-gb','CN-CN','ID-ID','US-US','IT-IT','MX-MX','PL-PL'], 'en-US'), 'en-US', init_time),
        encode_field(3, 6, 8),
        encode_field(4, 7, pack_15_16_bits(1280, 1280) + pack_15_16_bits(800, 752)),
        encode_field(5, 5, 24),
        encode_field(6, 5, 22),
        encode_field(7, 6, 1.5),
        encode_field(8, 7, n_digit_hex(0 // 15, 2) + n_digit_hex(0 // 15, 2)),
        encode_field(9, 7, n_digit_hex(2, 2) + n_digit_hex(mmh3.hash(''.join(sorted(['application/pdf', 'text/pdf']))), 8, stop=True)),
        encode_field(10, 7, n_digit_hex(5, 2) + n_digit_hex(mmh3.hash(''.join(sorted(['PDF ViewerPortable Document Format2internal-pdf-viewer', 'Chrome PDF ViewerPortable Document Format2internal-pdf-viewer', 'Chromium PDF ViewerPortable Document Format2internal-pdf-viewer', 'Microsoft Edge PDF ViewerPortable Document Format2internal-pdf-viewer', 'WebKit built-in PDFPortable Document Format2internal-pdf-viewer']))), 8, stop=True)),
        encode_field(11, 7, bits_to_hex([False, False, False, False, False, True, True, True, True, True, True, True])),
        encode_field(12, 7, encode_xxtea_frame(12, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36', init_time)),
        encode_field(13, 4, 'fb98c853', init_time),
        encode_field(14, 7, bits_to_hex([True, True, True])),
        encode_optional_index(17, index_of(['20030107', '20100101'], '20030107'), '20030107', init_time),
        encode_field(18, 4, '117f6743', init_time),
        encode_field(19, 4, 'ANGLE (Intel, Intel(R) Arc(TM) Graphics (0x00007D55) Direct3D11 vs_5_0 ps_5_0, D3D11)', init_time),
        encode_field(20, 4, '1970/3/1 9:00:00', init_time),
        encode_field(21, 7, bits_to_hex([False]*8)),
        encode_field(22, 5, 33),
        encode_field(24, 5, random.randint(10000, 13000)),
        encode_optional_index(25, index_of(['Maximum call stack size exceeded', 'Maximum call stack size exceeded.', 'too much recursion'], 'Maximum call stack size exceeded'), 'Maximum call stack size exceeded', init_time),
        encode_optional_index(26, index_of(['InternalError', 'RangeError', 'Error'], 'RangeError'), 'RangeError', init_time),
        encode_field(27, 5, 1034),
        encode_field(28, 7, '00'),
        encode_optional_index(29, index_of(["Cannot read property 'b' of undefined", "(void 0) is undefined", "undefined is not an object (evaluating '(void 0).b')", "Cannot read properties of undefined (reading 'b')"], "Cannot read properties of undefined (reading 'b')"), "Cannot read properties of undefined (reading 'b')", init_time),
        encode_field(30, 7, n_digit_hex(33, 2) + n_digit_hex(mmh3.hash(''.join(sorted(['vendorSub~~~function get vendorSub() { [native code] }', 'productSub~~~function get productSub() { [native code] }', 'vendor~~~function get vendor() { [native code] }', 'maxTouchPoints~~~function get maxTouchPoints() { [native code] }', 'scheduling~~~function get scheduling() { [native code] }', 'userActivation~~~function get userActivation() { [native code] }', 'geolocation~~~function get geolocation() { [native code] }', 'doNotTrack~~~function get doNotTrack() { [native code] }', 'connection~~~function get connection() { [native code] }', 'plugins~~~function get plugins() { [native code] }', 'mimeTypes~~~function get mimeTypes() { [native code] }', 'pdfViewerEnabled~~~function get pdfViewerEnabled() { [native code] }', 'webkitTemporaryStorage~~~function get webkitTemporaryStorage() { [native code] }', 'webkitPersistentStorage~~~function get webkitPersistentStorage() { [native code] }', 'hardwareConcurrency~~~function get hardwareConcurrency() { [native code] }', 'cookieEnabled~~~function get cookieEnabled() { [native code] }', 'appCodeName~~~function get appCodeName() { [native code] }', 'appName~~~function get appName() { [native code] }', 'appVersion~~~function get appVersion() { [native code] }', 'platform~~~function get platform() { [native code] }', 'product~~~function get product() { [native code] }', 'userAgent~~~function get userAgent() { [native code] }', 'language~~~function get language() { [native code] }', 'languages~~~function get languages() { [native code] }', 'onLine~~~function get onLine() { [native code] }', 'webdriver~~~function get webdriver() { [native code] }', 'getGamepads~~~function getGamepads() { [native code] }', 'javaEnabled~~~function javaEnabled() { [native code] }', 'sendBeacon~~~function sendBeacon() { [native code] }', 'vibrate~~~function vibrate() { [native code] }', 'windowControlsOverlay~~~function get windowControlsOverlay() { [native code] }', 'constructor~~~function Navigator() { [native code] }', 'toString~~~function toString() { [native code] }']))), 8, stop=True)),
        encode_field(31, 7, n_digit_hex(int(''.join(format(v & 3, '02b') for v in [2, 2, 0, 2, 1, 2, 2, 2]), 2), 4, True)),
    ]
    one = [
        encode_field(0, 3, 0),
        encode_optional_index(1, index_of(['America/New_York', 'America/Sao_Paulo', 'America/Chicago', 'America/Los_Angeles', 'America/Mexico_City', 'Asia/Shanghai'], 'Asia/Tokyo'), 'Asia/Tokyo', init_time),
        encode_optional_index(2, index_of(['US-US,US', 'US-US', 'BR-BR,BR,US-US,US', 'ES-ES,ES', 'CN-CN,CN'], 'en-US,ja,en,zh-CN,ay,ga'), 'en-US,ja,en,zh-CN,ay,ga', init_time),
        encode_field(6, 5, 6),
        encode_field(10, 7, bits_to_hex([True, False, True, False])),
        encode_field(12, 5, 80),
        encode_field(13, 7, bits_to_hex([False]*11)),
        encode_field(14, 2, ""),
        encode_field(16, 7, bits_to_hex([False]*9)),
        encode_field(17, 7, bits_to_hex([False, False, False, False, True, True, True, False, False, True, False, False, False, True, False])),
        encode_field(18, 2, ""),
        encode_field(21, 7, '01000000'),
        encode_field(22, 4, 'ja', init_time),
        encode_field(24, 7, n_digit_hex(0, 4) + n_digit_hex(1280 - 1280, 4)),
        encode_field(26, 1, ''),
        encode_field(27, 7, bits_to_hex([True, False, False, False])),
        encode_optional_index(28, index_of(['arm', 'x86'], 'x86'), 'x86', init_time),
        encode_field(29, 4, '', init_time),
        encode_field(30, 4, '142.0.7444.60', init_time),
    ]
    two = [
        encode_optional_index(0, index_of(["Android", "iOS", "macOS", "Linux", "Windows", "Unknown"], "Windows"), "Windows", init_time),
        encode_field(1, 4, "19.0.0", init_time),
        encode_optional_index(2, index_of(["Chromium", "Google Chrome", "Opera", "Brave", "Microsoft Edge"], "Google Chrome"), "Google Chrome", init_time),
        encode_field(3, 5, 0),
        encode_field(4, 5, datetime.datetime.fromtimestamp(init_time / 1000).minute),
        encode_field(5, 4, "x.com", init_time),
        encode_field(6, 7, encode_xxtea_frame(6, "{}", init_time)),
        encode_field(7, 7, bits_to_hex([True]*37 + [False]*9)),
        encode_field(8, 5, 2),
        encode_field(9, 5, 0),
        encode_field(10, 5, 13),
        encode_field(11, 5, 2790),
        encode_field(12, 7, n_digit_hex(9, 2) + ''.join('0000' + n_digit_hex(max(0, round(n * 1000)), 8, stop=True) for n in [0, 0, 0, 0, 1.399999976158142, 1.399999976158142, 1.399999976158142, 0, 70.19999998807907])),
        encode_field(13, 1, ""),
        encode_field(14, 7, bits_to_hex([False, False, False, False])),
        encode_optional_index(15, index_of(["Illegal invocation", "Can only call CanvasRenderingContext2D.getImageData on instances of CanvasRenderingContext2D", "'getImageData' called on an object that does not implement interface CanvasRenderingContext2D."], "Illegal invocation"), "Illegal invocation", init_time),
        encode_field(16, 7, n_digit_hex(2, 2) + ''.join('0000' + n_digit_hex(max(0, round(n * 1000)), 8, stop=True) for n in [3760000000, 91700000])),
        encode_field(17, 7, bits_to_hex([False, False, False, False, False, True, False, False])),
        encode_field(18, 7, pack_15_16_bits(1280, 1280) + pack_15_16_bits(665, 752)),
        encode_field(19, 7, n_digit_hex(0, 4) + n_digit_hex(0, 4)),
        encode_optional_index(20, index_of(['landscape-primary', 'portrait-primary', 'landscape-secondary', 'portrait-secondary'], 'landscape-primary'), 'landscape-primary', init_time),
        encode_field(21, 5, 0),
        encode_field(22, 7, n_digit_hex(15, 4) + n_digit_hex(15, 4)),
        encode_field(23, 7, '0000' + n_digit_hex(max(0, round(85 * 1000)), 8, stop=True)),
        encode_field(24, 4, 'en', init_time),
        encode_field(25, 5, 26),
        encode_field(26, 5, 7),
        encode_field(27, 5, 19),
        encode_optional_index(28, index_of(['macOS', 'Windows', 'ChromeOS', 'Android', 'Other'], 'Windows'), 'Windows', init_time),
        encode_field(29, 5, 82),
        encode_field(30, 4, '-1631965880', init_time),
    ]
    return [zero, one, two, [], []]


# ============ Fake Data ============
import json as _json
import os as _os
_FAKE_DATA = _json.load(open(_os.path.join(_os.path.dirname(__file__), '_fake_data.json')))
FAKE_TWO = _FAKE_DATA['two']
FAKE_EIGHT = _FAKE_DATA['eight']


# ============ CastleToken Class ============
class CastleToken:
    def __init__(self, init_time, cuid, fingerprint=None):
        self.init_time = init_time
        self.fingerprint = fingerprint or fingerprint_preset(init_time)
        self.cuid = cuid
        self.random_value = random.randint(0, 15)

    def create_token(self):
        zero = random.randint(0, 255)
        one = 5
        two = FAKE_TWO
        three = n_digit_hex(zero, 2)
        four = make_time_token(self.init_time, self.random_value)
        five = encode_to_4dig_hex(one)
        six = self.fingerprint
        seven = None
        eight = encode_3_arrs(*FAKE_EIGHT)
        data = [zero, one, two, three, four, five, six, seven, eight]

        v1 = make_time_token(int(time.time() * 1000), random.randint(0, 15))
        v2 = [v1, data[2]]
        v3 = func2(v2, data, self.cuid)
        return func4(func3(v3), data)
