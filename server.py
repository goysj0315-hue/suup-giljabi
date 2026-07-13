import openpyxl
import csv
import os
from mcp.server.fastmcp import FastMCP

port = int(os.environ.get("PORT", 8080))
mcp = FastMCP("수업길잡이", host="0.0.0.0", port=port, stateless_http=True)

wb = openpyxl.load_workbook("subject_data.xlsx", read_only=True, data_only=True)
ws = wb.active

def clean(v):
    s = str(v).strip() if v else ""
    return "" if s in ("-", "None") else s

subject_data = []
for row in ws.iter_rows(min_row=4, values_only=True):
    if row[2]:
        subject_data.append({
            "대학명": clean(row[2]),
            "모집단위": clean(row[3]),
            "계열": clean(row[4]),
            "핵심과목": clean(row[5]),
            "권장과목": clean(row[6]),
        })

school_data = []
with open("school_subjects.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        school_data.append(row)

def normalize_dept(dept):
    """학과명에서 핵심 키워드 추출: 컴퓨터공학과 -> 컴퓨터"""
    d = dept.strip()
    for suffix in ["학과", "학부", "공학과", "공학부", "과", "부", "계열", "전공"]:
        if d.endswith(suffix) and len(d) > len(suffix):
            d = d[:-len(suffix)]
            break
    return d.strip()

@mcp.tool()
def recommend_subjects(university: str, department: str) -> str:
    """Retrieves recommended high school subjects from 수업길잡이(SuupGilJabi) service for university admission. Given a target university and department, returns core and recommended subjects. university: 대학명 (예: 경희대, 서울대). department: 학과명 (예: 컴퓨터공학과, 의예과)"""
    univ = university.replace("학교", "").strip()
    dept_key = normalize_dept(department)

    results = [
        row for row in subject_data
        if univ in row["대학명"] and
        (dept_key in row["모집단위"] or dept_key in row["계열"] or
         department in row["모집단위"] or department in row["계열"])
    ]
    if not results:
        results = [
            row for row in subject_data
            if univ in row["대학명"]
        ]
        if results:
            depts = sorted(set(f"{r['모집단위']} {r['계열']}".strip() for r in results))
            return (f"'{university}'에서 '{department}'와 정확히 일치하는 모집단위를 찾지 못했습니다.\n"
                    f"이 대학의 모집단위 목록: {', '.join(depts[:30])}")
        return f"'{university} {department}'에 대한 정보를 찾을 수 없습니다."
    rows = []
    for row in results[:5]:
        core = row["핵심과목"] or "명시된 핵심과목 없음"
        recommended = row["권장과목"] or "명시된 권장과목 없음"
        rows.append(
            f"대학: {row['대학명']}\n"
            f"모집단위: {row['모집단위']} {row['계열']}\n"
            f"핵심과목: {core}\n"
            f"권장과목: {recommended}"
        )
    return "\n---\n".join(rows)

@mcp.tool()
def recommend_school(region: str, subjects: str) -> str:
    """Recommends high schools from 수업길잡이(SuupGilJabi) service based on 2025 curriculum data. Given a region and required subjects, returns top 5 high schools that offer those subjects. region: 지역명 (예: 서울특별시, 경기도). subjects: 과목들 쉼표로 구분 (예: 미적분,물리학Ⅰ)"""
    subject_list = [s.strip() for s in subjects.split(",") if s.strip()]
    regional_schools = [s for s in school_data if region in s["지역"]]
    if not regional_schools:
        regions = sorted(set(s["지역"] for s in school_data))
        return f"'{region}' 지역의 학교 정보를 찾을 수 없습니다. 사용 가능한 지역: {', '.join(regions)}"
    scored = []
    for school in regional_schools:
        school_subjects = school["개설과목"].split(",")
        matched = [sub for sub in subject_list if any(sub in s for s in school_subjects)]
        if matched:
            scored.append((len(matched), matched, school))
    if not scored:
        return f"'{region}'에서 해당 과목을 개설한 학교를 찾을 수 없습니다."
    scored.sort(key=lambda x: x[0], reverse=True)
    rows = []
    for score, matched, school in scored[:5]:
        rows.append(
            f"학교명: {school['학교명']}\n"
            f"지역: {school['지역']}\n"
            f"학교유형: {school['학교유형']}\n"
            f"개설확인과목: {', '.join(matched)} ({score}/{len(subject_list)}개)"
        )
    return "\n---\n".join(rows)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
