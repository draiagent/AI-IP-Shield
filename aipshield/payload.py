from __future__ import annotations

import binascii
from typing import Iterable

MAGIC = 0xA17E
MAGIC_BITS = 16
VERSION = 1
VERSION_BITS = 8
TOKEN_BITS = 64
CRC_BITS = 16
CORE_BITS = MAGIC_BITS + VERSION_BITS + TOKEN_BITS + CRC_BITS


def int_to_bits(value: int, n: int) -> list[int]:
    return [(value >> (n - 1 - i)) & 1 for i in range(n)]


def bits_to_int(bits: Iterable[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | (int(bit) & 1)
    return value


def _token_bytes(token: str) -> bytes:
    if len(token) != 16:
        raise ValueError("watermark token must be exactly 16 hexadecimal characters")
    try:
        return bytes.fromhex(token)
    except ValueError as exc:
        raise ValueError("watermark token must be hexadecimal") from exc


def encode_core(token: str) -> list[int]:
    token_b = _token_bytes(token)
    crc_input = bytes([VERSION]) + token_b
    crc = binascii.crc_hqx(crc_input, 0xFFFF)
    return (
        int_to_bits(MAGIC, MAGIC_BITS)
        + int_to_bits(VERSION, VERSION_BITS)
        + int_to_bits(int.from_bytes(token_b, "big"), TOKEN_BITS)
        + int_to_bits(crc, CRC_BITS)
    )


def decode_core(bits: Iterable[int]) -> str | None:
    data = list(int(x) & 1 for x in bits)
    if len(data) < CORE_BITS:
        return None
    data = data[:CORE_BITS]
    i = 0
    magic = bits_to_int(data[i:i + MAGIC_BITS]); i += MAGIC_BITS
    version = bits_to_int(data[i:i + VERSION_BITS]); i += VERSION_BITS
    token_int = bits_to_int(data[i:i + TOKEN_BITS]); i += TOKEN_BITS
    crc = bits_to_int(data[i:i + CRC_BITS])
    if magic != MAGIC or version != VERSION:
        return None
    token_b = token_int.to_bytes(8, "big")
    expected_crc = binascii.crc_hqx(bytes([version]) + token_b, 0xFFFF)
    if crc != expected_crc:
        return None
    return token_b.hex().upper()


def _hamming74_encode_nibble(d: list[int]) -> list[int]:
    # Positions 1,2,4 are parity; 3,5,6,7 carry d1..d4.
    d1, d2, d3, d4 = (int(x) & 1 for x in d)
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p4 = d2 ^ d3 ^ d4
    return [p1, p2, d1, p4, d2, d3, d4]


def _hamming74_decode_word(w: list[int]) -> tuple[list[int], bool]:
    b = [0] + [int(x) & 1 for x in w[:7]]
    s1 = b[1] ^ b[3] ^ b[5] ^ b[7]
    s2 = b[2] ^ b[3] ^ b[6] ^ b[7]
    s4 = b[4] ^ b[5] ^ b[6] ^ b[7]
    syndrome = s1 + (s2 << 1) + (s4 << 2)
    corrected = False
    if 1 <= syndrome <= 7:
        b[syndrome] ^= 1
        corrected = True
    return [b[3], b[5], b[6], b[7]], corrected


def hamming74_encode(bits: Iterable[int]) -> list[int]:
    data = list(int(x) & 1 for x in bits)
    if len(data) % 4:
        data += [0] * (4 - len(data) % 4)
    out: list[int] = []
    for i in range(0, len(data), 4):
        out.extend(_hamming74_encode_nibble(data[i:i + 4]))
    return out


def hamming74_decode(bits: Iterable[int], decoded_length: int) -> tuple[list[int], int]:
    data = list(int(x) & 1 for x in bits)
    words = (decoded_length + 3) // 4
    need = words * 7
    if len(data) < need:
        raise ValueError(f"need at least {need} encoded bits")
    out: list[int] = []
    corrected = 0
    for i in range(words):
        nibble, did_correct = _hamming74_decode_word(data[i * 7:(i + 1) * 7])
        out.extend(nibble)
        corrected += int(did_correct)
    return out[:decoded_length], corrected



def convolutional_encode(bits: Iterable[int]) -> list[int]:
    data = [int(x) & 1 for x in bits] + [0, 0]  # terminate K=3 trellis at state 0
    state = 0
    out: list[int] = []
    for u in data:
        p1 = (state >> 1) & 1
        p2 = state & 1
        out.append(u ^ p1 ^ p2)  # g0 = 111
        out.append(u ^ p2)       # g1 = 101
        state = (u << 1) | p1
    return out


def convolutional_decode(bits: Iterable[int], decoded_length: int) -> list[int]:
    data = [int(x) & 1 for x in bits]
    steps = decoded_length + 2
    need = steps * 2
    if len(data) < need:
        raise ValueError(f"need at least {need} encoded bits")
    data = data[:need]
    inf = 10**9
    metrics = [0, inf, inf, inf]
    paths: list[list[list[int] | None]] = []
    prev_states: list[list[int | None]] = []
    for t in range(steps):
        r0, r1 = data[2*t], data[2*t+1]
        new_metrics = [inf] * 4
        new_prev: list[int | None] = [None] * 4
        new_bit: list[int | None] = [None] * 4
        for st in range(4):
            if metrics[st] >= inf:
                continue
            p1 = (st >> 1) & 1
            p2 = st & 1
            for u in (0, 1):
                o0 = u ^ p1 ^ p2
                o1 = u ^ p2
                ns = (u << 1) | p1
                m = metrics[st] + (o0 != r0) + (o1 != r1)
                if m < new_metrics[ns]:
                    new_metrics[ns] = m
                    new_prev[ns] = st
                    new_bit[ns] = u
        metrics = new_metrics
        prev_states.append(new_prev)
        paths.append(new_bit)
    state = 0 if metrics[0] < inf else min(range(4), key=lambda x: metrics[x])
    decoded_rev: list[int] = []
    for t in range(steps - 1, -1, -1):
        bit = paths[t][state]
        prev = prev_states[t][state]
        if bit is None or prev is None:
            raise ValueError("convolutional decoder traceback failed")
        decoded_rev.append(int(bit))
        state = int(prev)
    decoded = list(reversed(decoded_rev))
    return decoded[:decoded_length]


def encoded_length(ecc: str = "none") -> int:
    if ecc == "none":
        return CORE_BITS
    if ecc == "hamming74":
        return ((CORE_BITS + 3) // 4) * 7
    if ecc == "conv12":
        return (CORE_BITS + 2) * 2
    raise ValueError(f"unknown ECC: {ecc}")


def encode_payload(token: str, total_bits: int | None = None, ecc: str = "none") -> list[int]:
    core = encode_core(token)
    if ecc == "none":
        payload = core
    elif ecc == "hamming74":
        payload = hamming74_encode(core)
    elif ecc == "conv12":
        payload = convolutional_encode(core)
    else:
        raise ValueError(f"unknown ECC: {ecc}")
    if total_bits is not None:
        if len(payload) > total_bits:
            raise ValueError(f"encoded payload requires {len(payload)} bits, capacity is {total_bits}")
        # Deterministic padding keeps BER comparisons meaningful without adding identity data.
        pad_seed = encode_core(token)
        j = 0
        while len(payload) < total_bits:
            payload.append(pad_seed[j % len(pad_seed)] ^ ((j // len(pad_seed)) & 1))
            j += 1
    return payload


def decode_payload(bits: Iterable[int], ecc: str = "none") -> str | None:
    data = list(int(x) & 1 for x in bits)
    if ecc == "none":
        return decode_core(data[:CORE_BITS])
    if ecc == "hamming74":
        need = encoded_length("hamming74")
        if len(data) < need:
            return None
        try:
            core, _ = hamming74_decode(data[:need], CORE_BITS)
        except ValueError:
            return None
        return decode_core(core)
    if ecc == "conv12":
        need = encoded_length("conv12")
        if len(data) < need:
            return None
        try:
            core = convolutional_decode(data[:need], CORE_BITS)
        except ValueError:
            return None
        return decode_core(core)
    raise ValueError(f"unknown ECC: {ecc}")
