"""
تشفير XXTEA + أدوات مساعدة
"""
import math
import base64
import re
from itertools import cycle


# ============ XXTEA ============
def xxtea_encrypt(e, t):
    def to_uint32_array(data):
        res = []
        for r in range(math.ceil(len(data) / 4)):
            val = (
                (data[r * 4] if r * 4 < len(data) else 0)
                | ((data[r * 4 + 1] if r * 4 + 1 < len(data) else 0) << 8)
                | ((data[r * 4 + 2] if r * 4 + 2 < len(data) else 0) << 16)
                | ((data[r * 4 + 3] if r * 4 + 3 < len(data) else 0) << 24)
            )
            res.append(val & 0xFFFFFFFF)
        return res

    v = to_uint32_array(e)
    n = len(v) - 1
    if n < 1:
        return v

    sum_val = 0
    z = v[n]
    DELTA = 2654435769
    mask = 0xFFFFFFFF

    rounds = 6 + 52 // (n + 1)
    for _ in range(rounds):
        sum_val = (sum_val + DELTA) & mask
        e_val = (sum_val >> 2) & 3
        p = 0
        while p < n:
            y = v[p + 1]
            mx = ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^ (
                (sum_val ^ y) + (t[p & 3 ^ e_val] ^ z)
            )
            v[p] = (v[p] + mx) & mask
            z = v[p]
            p += 1
        y = v[0]
        mx = ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^ (
            (sum_val ^ y) + (t[p & 3 ^ e_val] ^ z)
        )
        v[n] = (v[n] + mx) & mask
        z = v[n]
    return v


# ============ Hex Utils ============
def n_digit_hex(value, n, stop=False):
    if stop:
        max_value = 16 ** n - 1
        value = min(value, max_value)
    mask = (1 << (4 * n)) - 1
    return f'{value & mask:0{n}x}'


def xor_stream(data, key):
    key_cycle = cycle(key)
    result = ''
    for hex_digit, key_digit in zip(data, key_cycle):
        xor = int(hex_digit, 16) ^ int(key_digit, 16)
        result += format(xor, 'x')
    return result


def arr_to_2dig_hex_string(arr):
    return ''.join(map(lambda x: n_digit_hex(x, 2), arr))


def base64_encode(string):
    string = string.encode() if isinstance(string, str) else string
    return base64.b64encode(string).decode()


# ============ Fingerprint Encode ============
def to_byte_array_manual(int_array):
    result = []
    for num in int_array:
        num = num & 0xFFFFFFFF
        result.append(num & 255)
        result.append((num >> 8) & 255)
        result.append((num >> 16) & 255)
        result.append((num >> 24) & 255)
    return result


def time_index_encrypt(index, input_str, time_val):
    time_unsigned = time_val & 0xFFFFFFFF
    return to_byte_array_manual(
        xxtea_encrypt(input_str.encode(), [index, time_unsigned, 2107336303, 2241668600, 1517820919, 2554034554, 1164413191])
    )


def encode_xxtea_frame(index, data, time_val):
    xxtea_encrypted = time_index_encrypt(index, data, time_val)
    def calc_byte_length(n):
        length = 0
        while n != 0:
            n >>= 8
            length += 1
        return length
    byte_length = calc_byte_length(len(xxtea_encrypted))
    return (
        n_digit_hex(byte_length, 2)
        + n_digit_hex(len(xxtea_encrypted), 2)
        + arr_to_2dig_hex_string(xxtea_encrypted)
    )


def prepare_value(index, case):
    return n_digit_hex((index & 31) << 3 | case & 7, 2)


def encode_field(index, case, input_val, time_val=None):
    if case == 3:
        return prepare_value(index, 3) + n_digit_hex(input_val, 2)
    elif case == 4:
        arr = time_index_encrypt(index, input_val, time_val)
        return prepare_value(index, 4) + n_digit_hex(len(arr), 2) + arr_to_2dig_hex_string(arr)
    elif case == 5:
        if (input_val & 0x7FFF) > 127:
            num = (1 << 15) | (input_val & 0x7FFF)
            hex_val = n_digit_hex(num, 4)
        else:
            hex_val = n_digit_hex(input_val & 0xFF, 2)
        return prepare_value(index, 5) + hex_val
    elif case == 6:
        return prepare_value(index, 6) + n_digit_hex(round(input_val * 10), 2)
    elif case == 7:
        return prepare_value(index, 7) + input_val
    else:
        return prepare_value(index, case)


def index_of(arr, value):
    if value in arr:
        return arr.index(value)
    return -1


def encode_optional_index(index, input1, input2, time_val):
    if input1 == -1:
        return encode_field(index, 4, input2, time_val)
    return encode_field(index, 3, input1, time_val)


def bits_to_hex(bits):
    length_prefix = f'{len(bits) & 255:02x}'
    normalized_bits = list(map(bool, bits))
    body_hex = ''
    chunk_size = 24
    for i in range(0, len(normalized_bits), chunk_size):
        chunk = normalized_bits[i:i + chunk_size]
        val = 0
        for bit in chunk:
            val = (val << 1) | bit
        chunk_len = len(chunk)
        if chunk_len == chunk_size:
            num_bytes = 3
        else:
            num_bytes = math.ceil(chunk_len / 8)
        body_hex += n_digit_hex(val, num_bytes * 2)
    return length_prefix + body_hex


def pack_15_16_bits(value1, value2):
    v1_15bits = value1 & 32767
    v2_16bits = value2 & 65535
    if v1_15bits == v2_16bits:
        return n_digit_hex(v1_15bits | 32768, 4)
    else:
        return n_digit_hex(v1_15bits, 4) + n_digit_hex(v2_16bits, 4)


# ============ Float Utils ============
def float_to_hex(x):
    result = []
    quotient = int(x)
    fraction = x - quotient
    while quotient > 0:
        quotient = int(x / 16)
        remainder = int(x - (float(quotient) * 16))
        if remainder > 9:
            result.insert(0, chr(remainder + 55))
        else:
            result.insert(0, str(remainder))
        x = float(quotient)
    if fraction == 0:
        return ''.join(result)
    result.append('.')
    while fraction > 0:
        fraction *= 16
        integer = int(fraction)
        fraction -= float(integer)
        if integer > 9:
            result.append(chr(integer + 55))
        else:
            result.append(str(integer))
    return ''.join(result)


def is_odd(num):
    if num % 2:
        return -1.0
    return 0.0
