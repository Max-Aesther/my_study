from fastapi import FastAPI
import ezdxf
import os
from fastapi.middleware.cors import CORSMiddleware
import math
import re
from collections import defaultdict

app = FastAPI()

# app.main:app --reload

# cors 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)             

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/dxf")
def read_dxf():
    doc = ezdxf.readfile("도면1.dxf")
    msp = doc.modelspace()

    entities = []

    for e in msp:
        if e.dxftype() == "LINE":
            entities.append({
                "type": "LINE",
                "start": tuple(e.dxf.start),  # Vec3 → tuple 변환
                "end": tuple(e.dxf.end)
            })

        elif e.dxftype() == "CIRCLE":
            entities.append({
                "type": "CIRCLE",
                "center": tuple(e.dxf.center),  # Vec3 → tuple 변환
                "radius": e.dxf.radius
            })

        elif e.dxftype() == "ARC":
            entities.append({
                "type": "ARC",
                "center": tuple(e.dxf.center),
                "radius": e.dxf.radius,
                "start_angle": e.dxf.start_angle,
                "end_angle": e.dxf.end_angle
            })
        
        elif e.dxftype() == "LWPOLYLINE":  # ← 기둥 사각형
            entities.append({
                "type": "LWPOLYLINE",
                "layer": e.dxf.layer,
                "points": [tuple(p[:2]) for p in e.get_points()]
            })

        elif e.dxftype() == "TEXT":  # ← 부호 텍스트
            entities.append({
                "type": "TEXT",
                "layer": e.dxf.layer,
                "text": e.dxf.text,
                "position": tuple(e.dxf.insert)
            })

        elif e.dxftype() == "MTEXT":  # ← 멀티라인 텍스트
            entities.append({
                "type": "MTEXT",
                "layer": e.dxf.layer,
                "text": e.dxf.text,
                "position": tuple(e.dxf.insert)
            })

    return {"entities": entities}

# ─────────────────────────────────────────────
# 1. 상수 및 정규표현식 정의
# ─────────────────────────────────────────────

# 부재 타입 정의 (문제 정의 반영)
MEMBER_PATTERNS = [
    (r'MC\d*', 'H-BEAM, 주기둥'),
    (r'SC\d*', 'H-BEAM, 보조기둥'),
    (r'RSG\d*', 'H-BEAM, 강화큰보'),
    (r'SG\d*', 'H-BEAM, 큰보'),
    (r'B\d*', 'H-BEAM, 작은보'),
]

# H형강 규격 파싱 (H-400x200x8x13 등)
SPEC_PATTERN = re.compile(r'H[-–\s]*(\d+)[xX×\s]*(\d+)[xX×\s]*([\d./]+)[xX×\s]*([\d./]+)')

# 철의 밀도 (kg/cm³)
STEEL_DENSITY = 0.00785 

def calculate_h_beam_weight(h, b, t1, t2):
    """
    H형강의 단위 중량(kg/m) 계산
    공식: 단면적(cm2) * 0.785
    """
    # mm -> cm 변환
    h_cm, b_cm, t1_cm, t2_cm = h/10, b/10, t1/10, t2/10
    # 단면적 A = (h * t1) + 2 * (b - t1) * t2
    area = (h_cm * t1_cm) + 2 * (b_cm - t1_cm) * t2_cm
    return area * 7.85 # kg/m

def safe_float_convert(value_str):
    """'6/9' 같은 문자열을 평균값인 7.5로 변환하거나 '6'을 6.0으로 변환"""
    if '/' in value_str:
        # 슬래시로 나누어 각각 숫자로 변환 후 평균값 계산
        parts = [float(p) for p in value_str.split('/')]
        return sum(parts) / len(parts)
    return float(value_str)

# ─────────────────────────────────────────────
# 2. 분석 핵심 로직
# ─────────────────────────────────────────────

@app.get("/analyze_steel")
def analyze_dxf(filepath: str = "도면1.dxf", threshold: float = 500):
    try:
        doc = ezdxf.readfile(filepath)
    except:
        return {"error": "파일을 찾을 수 없습니다."}

    msp = doc.modelspace()
    geometries = []
    text_data = []

    # 1단계: 엔티티 수집
    for e in msp:
        etype = e.dxftype()
        if etype in ('LINE', 'LWPOLYLINE'):
            # 도형의 중심점 및 길이 계산
            if etype == 'LINE':
                p1, p2 = e.dxf.start, e.dxf.end
                center = ((p1.x + p2.x)/2, (p1.y + p2.y)/2)
                length = math.hypot(p1.x - p2.x, p1.y - p2.y)
            else: # LWPOLYLINE
                pts = e.get_points()
                if not pts: continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                center = (sum(xs)/len(xs), sum(ys)/len(ys))
                length = sum(math.hypot(pts[i][0]-pts[i+1][0], pts[i][1]-pts[i+1][1]) for i in range(len(pts)-1))

            geometries.append({'center': center, 'length': length, 'matched_labels': []})

        elif etype in ('TEXT', 'MTEXT'):
            txt = e.dxf.text.upper()
            pos = (e.dxf.insert.x, e.dxf.insert.y)
            
            # 부재명 찾기
            m_name = "기타 철골"
            for pat, name in MEMBER_PATTERNS:
                if re.search(pat, txt):
                    m_name = name
                    break
            
            # 규격 및 단위중량 파싱
            spec_str = "규격미정"
            unit_weight = 0
            m = SPEC_PATTERN.search(txt)
            if m:
                try:
                    # map(float, ...) 대신 safe_float_convert 사용
                    h = safe_float_convert(m.group(1))
                    b = safe_float_convert(m.group(2))
                    t1 = safe_float_convert(m.group(3))
                    t2 = safe_float_convert(m.group(4))
                    
                    spec_str = f"H-{int(h)}*{int(b)}*{m.group(3)}*{m.group(4)}"
                    unit_weight = calculate_h_beam_weight(h, b, t1, t2)
                except ValueError:
                    # 변환 실패 시 예외 처리
                    spec_str = "규격파싱실패"
                    unit_weight = 0
            
            text_data.append({'pos': pos, 'name': m_name, 'spec': spec_str, 'weight_m': unit_weight})

    # 2단계: 공간 매칭 (텍스트와 가장 가까운 도형 연결)
    for t in text_data:
        best_dist = threshold
        best_geom = None
        for g in geometries:
            dist = math.hypot(t['pos'][0] - g['center'][0], t['pos'][1] - g['center'][1])
            if dist < best_dist:
                best_dist = dist
                best_geom = g
        
        if best_geom:
            best_geom['matched_labels'].append(t)

    # 3단계: 물량 집계 (이미지 형식 데이터 구성)
    final_report = defaultdict(float)
    
    for g in geometries:
        # 매칭된 텍스트가 없으면 무시 (문제정의 2번 반영)
        # 매칭된 텍스트가 여러개면 중복 처리 (문제정의 6번 반영)
        for label in g['matched_labels']:
            key = (label['name'], label['spec'])
            # 물량(KG) = 길이(m) * 단위중량(kg/m)
            weight_kg = (g['length'] / 1000) * label['weight_m']
            final_report[key] += weight_kg

    # 4단계: 결과 포맷팅
    output = []
    for (name, spec), total_kg in final_report.items():
        output.append({
            "품명": name,
            "규격": spec,
            "단위": "KG",
            "수량": f"{total_kg:,.0f}" # 콤마 및 정수 표기
        })

    return {"철골공사_물량산출서": output}