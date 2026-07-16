# -*- coding: utf-8 -*-
"""Prototype: Arabic pharma product name normalization + attribute extraction."""
import re
import pandas as pd

# ---------- Layer 1: orthographic normalization ----------
DIACRITICS = re.compile(r'[\u064B-\u0652\u0670\u0640]')  # tashkeel + tatweel

def normalize_ar(text: str) -> str:
    t = str(text)
    t = DIACRITICS.sub('', t)
    t = (t.replace('أ','ا').replace('إ','ا').replace('آ','ا')
           .replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي'))
    # eastern arabic digits -> western
    t = t.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789'))
    t = t.lower()
    # split glued letter<->digit boundaries: 'اتورستات40م14ق' -> 'اتورستات 40م 14ق'
    t = re.sub(r'(?<=[\u0600-\u06FF])(?=\d)', ' ', t)
    t = re.sub(r'(?<=\d)(?=[\u0600-\u06FF])', '', t)  # keep unit attached to its number
    # noise tokens: س ج / س--ج / ج س variants (price-tag markers)
    t = re.sub(r'\bس[\s\-\.]*[جق](?=\s|$|/)', ' ', t)
    t = re.sub(r'\bج[\s\-\.]*س(?=\s|$|/)', ' ', t)
    t = re.sub(r'[^\w\u0600-\u06FF%./]+', ' ', t)   # punctuation -> space (keep % . /)
    # canonicalize pack-unit shorthand (digit context makes single letters unambiguous):
    # 4ش -> 4 شريط, 30ق -> 30 قرص, 14ك -> 14 كبسول, 3امب -> 3 امبول
    t = re.sub(r'(\d+)\s*(?:شرايط|شرائط|شريط|ش)(?=\s|$|/)', r'\1 شريط', t)
    t = re.sub(r'(\d+)\s*(?:اقراص|قرص|ق)(?=\s|$|/)',        r'\1 قرص', t)
    t = re.sub(r'(\d+)\s*(?:كبسولات|كبسوله|كبسول|كب|ك)(?=\s|$|/)', r'\1 كبسول', t)
    t = re.sub(r'(\d+)\s*(?:امبولات|امبول|امب)(?=\s|$|/)',  r'\1 امبول', t)
    t = re.sub(r'(\d+)\s*(?:اكياس|كيس)(?=\s|$|/)',          r'\1 كيس', t)
    # unify standalone Latin-letter-name tokens (drug variant suffixes): دي -> د, بي -> ب
    t = re.sub(r'(?<![\w\u0600-\u06FF])دي(?![\w\u0600-\u06FF])', 'د', t)
    t = re.sub(r'(?<![\w\u0600-\u06FF])بي(?![\w\u0600-\u06FF])', 'ب', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# ---------- Layer 2: attribute extraction ----------
FORM_MAP = {
    'tablet':  ['قرص','اقراص','tab','اقرص','شريط','شرائط','شرايط'],
    'capsule': ['كبسول','كبسوله','كب','كبس','caps','كبسولات'],
    'syrup':   ['شراب','syrup'],
    'ointment':['مرهم','oint'],
    'cream':   ['كريم','كريمه','cream'],
    'drops':   ['نقط','نقاط','قطره','drops'],
    'injection':['حقن','امبول','فيال','inj','امبولات'],
    'sachet':  ['اكياس','كيس','فوار','sachet','ساشيه'],
    'gel':     ['جل','جيل'],
    'spray':   ['سبراي','بخاخ','spray'],
    'suppository':['لبوس','اقماع'],
    'lotion':  ['لوسيون','محلول'],
    'milk':    ['لبن','حليب'],
}
FORM_LOOKUP = {alias: canon for canon, aliases in FORM_MAP.items() for alias in aliases}

STRENGTH_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*(?:/\s*(\d+(?:[.,]\d+)?))?\s*'
    r'(مجم|مج|ملجم|ملج|جم|جرام|مل|ملي|mg|gm|g|ml|mcg|ميكروجرام|وحده|%|م(?=\d|\s|$))'
)
PACK_RE = re.compile(r'(\d+)\s*(قرص|اقراص|ق|كبسول|كبسوله|كب|ك|كيس|اكياس|امبول|امب|شريط|شرايط|شرائط|ش|فيال|tab|caps)(?=\s|$|/)')

UNIT_CANON = {'مجم':'mg','مج':'mg','ملجم':'mg','ملج':'mg','م':'mg','mg':'mg',
              'جم':'g','جرام':'g','gm':'g','g':'g',
              'مل':'ml','ملي':'ml','ml':'ml','mcg':'mcg','ميكروجرام':'mcg',
              '%':'%','وحده':'iu'}

def extract_attributes(raw: str) -> dict:
    norm = normalize_ar(raw)
    manufacturer = None
    core = norm
    # manufacturer suffix after final slash, if non-numeric
    if '/' in norm:
        head, _, tail = norm.rpartition('/')
        if tail and not re.search(r'\d', tail) and len(tail) > 2:
            manufacturer, core = tail.strip(), head.strip()
    # strength
    strength = None
    m = STRENGTH_RE.search(core)
    if m:
        v1, v2, unit = m.group(1), m.group(2), UNIT_CANON.get(m.group(3), m.group(3))
        strength = f"{v1}/{v2}{unit}" if v2 else f"{v1}{unit}"
    # fallback: standalone number with NO unit (e.g. 'تلفاست 180') -> strength with unspecified unit
    if strength is None:
        consumed = set()
        for p in PACK_RE.finditer(core):
            consumed.add(p.group(1))
        bare = [n for n in re.findall(r'(?<![\d./])(\d{1,4})(?![\d./%])(?!\s*(?:قرص|اقراص|ق|كبسول|كب|ك|كيس|اكياس|امبول|شريط|ش|مل|جم|فيال))', core)
                if n not in consumed and 1 <= int(n) <= 2000]
        if len(bare) == 1:
            strength = f"{bare[0]}u"
    # form
    form = None
    for tok in core.split():
        if tok in FORM_LOOKUP:
            form = FORM_LOOKUP[tok]
            break
    # size marker (big/small/medium pack variants are distinct SKUs)
    size_marker = None
    for sm in ('كبير','صغير','وسط','كبيره','صغيره'):
        if sm in core.split():
            size_marker = {'كبيره':'كبير','صغيره':'صغير'}.get(sm, sm)
            break
    # pack size
    pack = None
    p = PACK_RE.search(core)
    if p:
        pack = int(p.group(1))
    # base name: tokens before first digit/strength/form token
    base_tokens = []
    for tok in core.split():
        if re.search(r'\d', tok) or tok in FORM_LOOKUP:
            break
        base_tokens.append(tok)
    base = ' '.join(base_tokens) if base_tokens else core.split()[0]
    return {'raw': raw, 'normalized': norm, 'core': core, 'base_name': base,
            'strength': strength, 'form': form, 'pack_size': pack,
            'size_marker': size_marker, 'manufacturer': manufacturer}

if __name__ == '__main__':
    df = pd.read_csv('clean_sales.csv')
    names = df['product_name'].drop_duplicates()
    print(f"{len(names)} distinct raw names")
    res = pd.DataFrame([extract_attributes(n) for n in names])
    res.to_csv('extraction_preview.csv', index=False)
    cov = {c: f"{res[c].notna().mean()*100:.0f}%" for c in ['strength','form','pack_size','manufacturer']}
    print("extraction coverage:", cov)


def strength_state(a, b):
    """Numeric-aware strength comparison: '180u' matches '180mg' (same number,
    one unit unspecified); '180mg' vs '120mg' or '180mg' vs '180ml' conflict."""
    import pandas as pd, re as _re
    if pd.isna(a) and pd.isna(b): return 'both_missing'
    if pd.isna(a) or pd.isna(b):  return 'one_missing'
    pa = _re.match(r'([\d./,]+)(\D*)$', str(a)); pb = _re.match(r'([\d./,]+)(\D*)$', str(b))
    if not pa or not pb: return 'match' if a == b else 'conflict'
    na, ua = pa.group(1), pa.group(2); nb, ub = pb.group(1), pb.group(2)
    # bare number vs weight/volume pack units (g, ml): incomparable, not a true
    # disagreement (نيستوجين 1 vs نيستوجين 1 400جم) -> treat as one_missing (HITL-able)
    if ('u' in (ua, ub)) and (ua in ('g','ml') or ub in ('g','ml')):
        return 'one_missing'
    if na != nb: return 'conflict'
    if ua == ub or ua == 'u' or ub == 'u': return 'match'
    return 'conflict'
