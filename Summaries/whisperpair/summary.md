# One Tap to Hijack Them All: A Security Analysis of the Google Fast Pair Protocol

**Summary:** The first comprehensive field study of Google's Fast Pair Service shows that 68% of certified Bluetooth accessories fail to enforce the protocol's core pairing-state check, enabling a family of "WhisperPair" attacks that silently hijack audio, access microphones, and covertly turn victims' own earbuds into long-term location trackers.

## Introduction
Google Fast Pair Service (GFPS) adds "one-tap" Bluetooth setup and Google-account synchronisation on top of BLE/Bluetooth Classic, but its primary authorisation boundary rests on a fragile application-layer rule rather than cryptography: a Provider (accessory) should accept a new unauthorised host's Key-based Pairing request only when it is explicitly in pairing mode. The authors show this predicate is systematically not enforced across the certified-device ecosystem and propose IntentPair, a lightweight modification that cryptographically binds the user's pairing intent into the key schedule so that unsolicited pairing fails by design.

## What they did
- Performed the first in-the-wild security analysis of GFPS, deriving three security invariants from the specification (pairing-state predicate, ownership/account association, user-facing signalling).
- Built an automated conformance test harness on a Raspberry Pi 4 (BlueZ) running three checks: pairing-state predicate enforcement, nonce reuse, and invalid-curve handling.
- Reverse-engineered the undocumented Google metadata API to retrieve per-model Anti-Spoofing public keys, bypassing IP rate-limiting via multiple addresses to enumerate certified models (and finding one not-yet-announced device).
- Designed and implemented WhisperPair, an attack family combining forced audio takeover, microphone access, audio-switch abuse, and covert Find Hub account binding for cross-ecosystem location tracking.
- Evaluated 25 commercial accessories (earbuds, headphones, speakers) from 16 vendors spanning 17 distinct Bluetooth chipsets from 7 chip-makers (see Table 1), and traced root causes across the implementation, validation, and certification stages of Google's compliance chain.
- Proposed and formalised IntentPair (with game-based security proofs deferred to an appendix), plus an authenticated re-pair path for already-bonded devices.

## Key findings & results
- 17 of 25 accessories (68%) fail the pairing-state predicate and accept unauthorised pairing while in steady state, without any user interaction; Figure 3 illustrates the live hijack.
- On every hijacked device the microphone was accessible (100% success), and audio switching was exploitable on all 6 devices that support it.
- All 4 devices supporting Google's Find Hub could be silently bound to the attacker's account for covert tracking; in one experiment a victim (an iPhone user wearing Pixel Buds Pro 2) was tracked across several cities for roughly 48 hours before any anti-stalking alert appeared (Figure 4).
- Time-to-hijack across five trials per device ranged from about 6 to 35 seconds (median ~10 s), succeeding at 14 m in the testbed; shorter distances gave identical results.
- 17 devices (68%) mishandle nonce validation (6 accept a reused nonce within a session, 6 accept any repeat), while all 25 passed the invalid-curve check.
- Security did not track price (Sony's flagship WH-1000XM6 was fully vulnerable while HP's cheaper Poly VFree 60 resisted entirely); Qualcomm-based devices were the most robust.
- Google acknowledged the findings, classified them as critical, and assigned CVE-2025-36911; it reported patching its Validator app and updating certification tests.

## Methodology & limitations
The attacker is a proximal Dolev–Yao adversary with commodity hardware (smartphone/laptop/Raspberry Pi), no physical access and no prior pairing; the audio/hijack attacks need no user interaction, while covert Find Hub enrolment specifically targets accessories that have never been paired with an Android device (so the attacker can claim the permanent Owner Account Key). The authors deliberately scoped to three conformance tests and state these do not rule out other protocol- or implementation-level weaknesses. They could not run Google's Validator app themselves (manufacturer-restricted), and the 25-device sample was chosen to maximise chipset/vendor diversity rather than for breadth, so ecosystem-wide claims rest partly on the observation that Fast Pair logic is widely reused across shared SDKs and chipset integrations; the IntentPair security proofs are relegated to an appendix not shown in the main text.

## About the authors
The work comes from KU Leuven's COSIC and DistriNet groups (Leuven, Belgium); co-first author Sayon Duttagupta is an early-career KU Leuven researcher (OpenAlex shows roughly 8 works and an h-index around 2, though the record mixes some unrelated affiliations and should be read with caution), while senior author Bart Preneel is a very prominent cryptographer at KU Leuven/COSIC with about 1,050 works, an h-index near 73 and over 22,000 citations.

## Publication & credibility
No venue name is printed in the extracted text, but the artefact-evaluation badges ("Available / Functional / Reproduced"), the CVE assignment, the coordinated 150-day disclosure, and the IEEE-style references strongly suggest a top-tier peer-reviewed security venue (the format is most consistent with the IEEE Symposium on Security & Privacy / "Oakland"); this cannot be confirmed from the source alone. If it is S&P (or a comparable flagship such as USENIX Security, CCS, or NDSS) the venue is top-tier and highly selective; if it is currently only a preprint/artefact release, treat it as not-yet-formally-vetted — though the documented Google collaboration and CVE lend the findings independent credibility regardless of venue.
