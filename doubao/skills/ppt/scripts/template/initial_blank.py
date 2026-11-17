"""Conservative retained-first-blank selection from one official deck read."""
import xml.etree.ElementTree as ET


def initial_blank_target(response, deck):
    def local(tag):
        if tag.startswith('{') and not tag[1:].split('}', 1)[0].endswith('/sml/2.0'):
            return tag
        return tag.rsplit('}', 1)[-1]

    data = response.get('data') if isinstance(response, dict) else None
    identity = data.get('xml_presentation_id') if isinstance(data, dict) else None
    if identity is not None and not isinstance(identity, str):
        return {'status': 'identity_unverified'}
    if identity and identity.strip() and identity != str(deck):
        return {'status': 'wrong_deck', 'expected': str(deck), 'actual': identity}
    if not isinstance(data, dict) or response.get('ok') is not True or data.get('scope') not in (None, 'presentation'):
        return {'status': 'read_unavailable'}
    document = data.get('xml_presentation')
    content = document.get('content') if isinstance(document, dict) else document
    if not isinstance(content, str):
        content = next((data[k] for k in ('xml', 'content', 'xml_content') if isinstance(data.get(k), str)), None)
    try:
        root = ET.fromstring(content)
    except (TypeError, ET.ParseError):
        return {'status': 'read_unavailable'}
    if local(root.tag) != 'presentation':
        return {'status': 'read_unavailable'}
    identities = [v for v in (identity, root.get('id'), root.get('xml_presentation_id'), root.get('presentation_id')) if v and v.strip()]
    if any(str(v) != str(deck) for v in identities):
        return {'status': 'wrong_deck', 'expected': str(deck), 'actual': next(v for v in identities if str(v) != str(deck))}
    if not identities:
        return {'status': 'identity_unverified'}
    slides = [n for n in root.iter() if local(n.tag) == 'slide']
    if not slides:
        return {'status': 'no_slides'}
    if len(slides) != 1:
        return {'status': 'multiple_slides', 'slide_count': len(slides)}
    slide = slides[0]
    if slide not in list(root) or not (slide.get('id') or '').strip() or any(
            local(n.tag) not in ('style', 'data', 'note') for n in slide) or sum(
            local(n.tag) == 'data' for n in slide) > 1:
        return {'status': 'blank_unverified'}
    # Preserve any data object, unknown child, visible text or speaker notes.
    if any(len(n) for n in slide if local(n.tag) == 'data') or any(
            (n.text and n.text.strip()) or (n.tail and n.tail.strip())
            or any(n.get(k) for k in ('src', 'token', 'href')) for n in slide.iter()) or any(
            local(child.tag) not in ('note', 'content', 'p', 'span')
            for note in slide if local(note.tag) == 'note' for child in note.iter()):
        return {'status': 'existing_content'}
    return {'status': 'reused', 'slide_id': slide.get('id')}
