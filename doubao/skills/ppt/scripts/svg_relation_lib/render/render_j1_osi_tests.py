"""Render 4 J1_osi hero SVGs · baseline + 3 test variants.

Emits to `final_svg_relation/04_J1_osi/step2_codified/`. Verifies:
  * baseline = OSI 7-layer with TCP/IP panel + encapsulation strip
  * dense   = 8-layer OSI extension (adds a Security layer)
  * sparse  = 4-layer TCP/IP (Application / Transport / Internet / Link)
  * minimal = 5-layer OSI, no TCP/IP panel, no encap strip
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from svg_relation_lib.presets.hero_embed_04_J1_osi_v2 import (
    BASELINE_ENCAP,
    build_osi_data,
    render_hero_embed_j1_osi_v2,
)


# Step1 references live at the workspace root · not under lark-slides-jw.
# Emit alongside step1_reference/ so step2_codified/ sits at the same level.
OUT_DIR = (
    _HERE.parent.parent
    / "final_svg_relation"
    / "04_J1_osi"
    / "step2_codified"
)


def _write(name: str, svg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(svg, encoding="utf-8")
    print(f"wrote {OUT_DIR / name}  ({len(svg)} bytes)")


# ═══════════════════════════════════════════════════════════════════
# baseline · full 7-layer OSI (uses HERO_J1_DATA default)
# ═══════════════════════════════════════════════════════════════════
def render_baseline() -> str:
    return render_hero_embed_j1_osi_v2(build_osi_data())


# ═══════════════════════════════════════════════════════════════════
# dense · 8-layer OSI extension (adds a Security layer between L6 & L5)
# ═══════════════════════════════════════════════════════════════════
def render_dense() -> str:
    layers = [
        {"no": 8, "short": "L8", "name": "Policy · User Intent",
         "hue": "indigo",
         "purpose": "Human intent · consent · regulatory scope",
         "pdu": "INTENT",
         "protocols": "OAuth · SAML · consent record · policy tag",
         "note": "The half-joke top layer — where humans actually live",
         "tcpip_key": "app"},
        {"no": 7, "short": "L7", "name": "Application", "hue": "purple",
         "purpose": "User-facing services · what apps talk",
         "pdu": "DATA",
         "protocols": "HTTP · SMTP · DNS · SSH · FTP",
         "note": "Browsers, mail clients, APIs — the intent surface",
         "tcpip_key": "app"},
        {"no": 6, "short": "L6", "name": "Presentation", "hue": "teal",
         "purpose": "Syntax translation · encoding · encryption",
         "pdu": "DATA",
         "protocols": "TLS · SSL · JPEG · ASCII · MIME",
         "note": "Serialize, compress, cipher — talk a common tongue",
         "tcpip_key": "app"},
        {"no": 5, "short": "L5", "name": "Session", "hue": "green",
         "purpose": "Dialog control · checkpoints · resume",
         "pdu": "DATA",
         "protocols": "NetBIOS · RPC · SOCKS · SIP",
         "note": "Open, keep, tear down conversations between hosts",
         "tcpip_key": "app"},
        {"no": 4, "short": "L4", "name": "Transport", "hue": "gold",
         "purpose": "End-to-end delivery · ports · reliability",
         "pdu": "SEGMENT / DATAGRAM",
         "protocols": "TCP · UDP · QUIC · SCTP",
         "note": "Ports, flow control, retransmit — TCP reliable, UDP fast",
         "tcpip_key": "transport"},
        {"no": 3, "short": "L3", "name": "Network", "hue": "navy",
         "purpose": "Routing between networks · logical addressing",
         "pdu": "PACKET",
         "protocols": "IPv4 · IPv6 · ICMP · OSPF · BGP",
         "note": "IP address, routing tables — hop across subnets",
         "tcpip_key": "internet"},
        {"no": 2, "short": "L2", "name": "Data Link", "hue": "brick",
         "purpose": "Node-to-node frames · MAC addressing",
         "pdu": "FRAME",
         "protocols": "Ethernet · Wi-Fi · PPP · ARP · VLAN",
         "note": "MAC address, error detect — one link, one hop",
         "tcpip_key": "link"},
        {"no": 1, "short": "L1", "name": "Physical", "hue": "red",
         "purpose": "Raw signal · voltage · wavelength · pins",
         "pdu": "BIT",
         "protocols": "RJ-45 · Fiber · 802.11 radio · DSL",
         "note": "Copper, glass, air — where electrons and photons live",
         "tcpip_key": "link"},
    ]
    return render_hero_embed_j1_osi_v2(build_osi_data(
        layers=layers,
        figure_title="OSI + intent layer · eight-layer extended stack",
        figure_subtitle=(
            "The half-joke L8 formalised · policy & consent sit above "
            "application intent · PDU = protocol data unit · illustrative"
        ),
        figure_note=(
            "8 layers · OSI 7 stack + policy/intent · TCP/IP mapping on the "
            "right · encapsulation strip below"
        ),
        footer_note=(
            "Notes.  L8 is a common joke among network engineers to describe "
            "the human policy layer. In real audit stacks it appears as "
            "consent records, policy tags and OAuth scopes attached to the "
            "L7 headers.  Figure 04 · dense variant"
        ),
    ))


# ═══════════════════════════════════════════════════════════════════
# sparse · 4-layer TCP/IP (no separate presentation / session / physical)
# ═══════════════════════════════════════════════════════════════════
def render_sparse() -> str:
    layers = [
        {"no": 4, "short": "L4", "name": "Application", "hue": "purple",
         "purpose": "HTTP · TLS · DNS · gRPC · streaming media",
         "pdu": "DATA",
         "protocols": "HTTP · TLS · DNS · SMTP · gRPC",
         "note": "Where most application code sits · kernel boundary above",
         "tcpip_key": "app"},
        {"no": 3, "short": "L3", "name": "Transport", "hue": "gold",
         "purpose": "End-to-end delivery · ports · reliability",
         "pdu": "SEGMENT / DATAGRAM",
         "protocols": "TCP · UDP · QUIC · SCTP",
         "note": "Ports, retransmit · TCP reliable, UDP/QUIC fast",
         "tcpip_key": "transport"},
        {"no": 2, "short": "L2", "name": "Internet", "hue": "navy",
         "purpose": "Routing between networks · logical addressing",
         "pdu": "PACKET",
         "protocols": "IPv4 · IPv6 · ICMP · BGP · OSPF",
         "note": "IP address, routing tables · hop across subnets",
         "tcpip_key": "internet"},
        {"no": 1, "short": "L1", "name": "Link", "hue": "brick",
         "purpose": "Frames on the wire · NIC & driver level",
         "pdu": "FRAME / BIT",
         "protocols": "Ethernet · Wi-Fi · MAC · cabling · radio",
         "note": "NIC drivers and firmware live here",
         "tcpip_key": "link"},
    ]
    # collapse TCP/IP mapping to a legend showing OSI absorption
    tcpip_groups = [
        {"key": "app", "label": "OSI L7-L5",  "hue": "purple",
         "note": "Application + Presentation + Session bundled here",
         "body": [
             "TLS, gRPC and codecs live inside HTTP libraries",
             "Kernel boundary sits above this line",
         ]},
        {"key": "transport", "label": "OSI L4", "hue": "gold",
         "note": "", "body": ["TCP · UDP · QUIC · same as OSI L4"]},
        {"key": "internet", "label": "OSI L3", "hue": "navy",
         "note": "", "body": ["IP · ICMP · BGP · maps to OSI L3"]},
        {"key": "link", "label": "OSI L2 + L1", "hue": "brick",
         "note": "TCP/IP fuses Data Link + Physical",
         "body": [
             "Ethernet · Wi-Fi · MAC · cabling · radio",
             "NIC drivers and firmware live here",
         ]},
    ]
    return render_hero_embed_j1_osi_v2(build_osi_data(
        layers=layers,
        figure_title="TCP/IP · four-layer stack · as shipped in the kernel",
        figure_subtitle=(
            "The pragmatic view · L5 / L6 collapsed into application "
            "libraries · L1 / L2 fused into the NIC driver · illustrative"
        ),
        figure_note=(
            "4 layers · TCP/IP kernel view · OSI mapping on the right · "
            "encapsulation strip below"
        ),
        tcpip_title="OSI MAPPING",
        tcpip_groups=tcpip_groups,
        encap_frames=BASELINE_ENCAP,
        footer_note=(
            "Notes.  TCP/IP is what actually ships in the Linux and Windows "
            "kernels · seven-layer OSI is a teaching scaffold · both models "
            "describe the same bits on the wire.  Figure 04 · sparse variant"
        ),
    ))


# ═══════════════════════════════════════════════════════════════════
# minimal · 5-layer OSI · no TCP/IP mapping panel · no encap strip
# ═══════════════════════════════════════════════════════════════════
def render_minimal() -> str:
    layers = [
        {"no": 5, "short": "L5", "name": "Application", "hue": "purple",
         "purpose": "HTTP · gRPC · streaming media",
         "pdu": "DATA",
         "protocols": "HTTP · gRPC · WebSocket · MQTT",
         "note": "Where the user-visible service lives",
         "tcpip_key": ""},
        {"no": 4, "short": "L4", "name": "Transport", "hue": "gold",
         "purpose": "End-to-end delivery · ports · reliability",
         "pdu": "SEGMENT",
         "protocols": "TCP · UDP · QUIC",
         "note": "Ports, retransmit, flow control",
         "tcpip_key": ""},
        {"no": 3, "short": "L3", "name": "Network", "hue": "navy",
         "purpose": "Routing between networks",
         "pdu": "PACKET",
         "protocols": "IPv4 · IPv6 · ICMP · BGP",
         "note": "Routing tables · hop across subnets",
         "tcpip_key": ""},
        {"no": 2, "short": "L2", "name": "Data Link", "hue": "brick",
         "purpose": "Node-to-node frames · MAC addressing",
         "pdu": "FRAME",
         "protocols": "Ethernet · Wi-Fi · PPP",
         "note": "MAC address, error detect",
         "tcpip_key": ""},
        {"no": 1, "short": "L1", "name": "Physical", "hue": "red",
         "purpose": "Raw signal · voltage · wavelength · pins",
         "pdu": "BIT",
         "protocols": "RJ-45 · Fiber · 802.11 radio",
         "note": "Copper, glass, air",
         "tcpip_key": ""},
    ]
    return render_hero_embed_j1_osi_v2(build_osi_data(
        layers=layers,
        figure_title="Five-layer network stack · teaching minimal",
        figure_subtitle=(
            "Presentation and Session omitted · reduced OSI · "
            "no TCP/IP mapping · no encapsulation strip · illustrative"
        ),
        figure_note=(
            "5 layers · OSI teaching minimal · L6/L5 omitted · "
            "no side panel · no encapsulation strip"
        ),
        tcpip_groups=[],
        encap_enabled=False,
        encap_frames=[],
        footer_note=(
            "Notes.  Introductory course version of the OSI stack · "
            "L6/L5 are usually taught later once TLS and SSL become "
            "relevant.  Figure 04 · minimal variant"
        ),
    ))


def main() -> None:
    _write("baseline.svg", render_baseline())
    _write("osi_test1_dense_8layer.svg", render_dense())
    _write("osi_test2_sparse_tcpip.svg", render_sparse())
    _write("osi_test3_minimal_no_mapping.svg", render_minimal())


if __name__ == "__main__":
    main()
