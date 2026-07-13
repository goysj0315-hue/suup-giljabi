import openpyxl
import csv
import uvicorn
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("수업길잡이")

wb = openpyxl.load_workbook("subject_data.xlsx", read_only=True, data_only=True)
ws = wb.active

subject_data = []
for row in ws.iter_rows(min_row=4, values_only=True):
    if row[2]:
        subject_data.append({
            "대학명": str(row[2]) if row[2] else "",
            "모집단위": str(row[3]) if row[3] else "",
            "계열": str(row[4]) if row[4] else "",
            "핵심과목": str(row[5]) if row[5] else "정보없음",
            "권장과목": str(row[6]) if row[6] else "정보없음",
        })

school_data = []
with open("school_subjects.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        school_data.append(row)

@mcp.tool()
def recommend_subjects(university: str, department: str) -> str:
    """Retrieves recommended subjects from 수업길잡이(수업길잡이) service. Given a target university and department, returns core and recommended subjects. university: 대학명 (예: 경희대, 서울대). department: 학과명 (예: 컴퓨터공학과, 의예과)"""
    results = [
        row for row in subject_data
        if university in row["대학명"] and
        department in (row["모집단위"] + " " + row["계열"])
    ]
    if not results:
        return f"'{university} {department}'에 대한 정보를 찾을 수 없습니다."
    rows = []
    for row in results:
        rows.append(
            f"대학: {row['대학명']}\n"
            f"모집단위: {row['모집단위']} {row['계열']}\n"
            f"핵심과목: {row['핵심과목']}\n"
            f"권장과목: {row['권장과목']}"
        )
    return "\n---\n".join(rows)

@mcp.tool()
def recommend_school(region: str, subjects: str) -> str:
    """Recommends high schools from 수업길잡이(수업길잡이) service. Given a region and required subjects, returns top 5 high schools. region: 지역명 (예: 서울특별시, 경기도). subjects: 과목들 쉼표로 구분 (예: 미적분,물리학Ⅰ)"""
    subject_list = [s.strip() for s in subjects.split(",")]
    regional_schools = [s for s in school_data if region in s["지역"]]
    if not regional_schools:
        return f"'{region}' 지역의 학교 정보를 찾을 수 없습니다."
    scored = []
    for school in regional_schools:
        school_subjects = school["개설과목"].split(",")
        match_count = sum(1 for sub in subject_list if any(sub in s for s in school_subjects))
        if match_count > 0:
            scored.append((match_count, school))
    if not scored:
        return f"'{region}'에서 해당 과목을 개설한 학교를 찾을 수 없습니다."
    scored.sort(key=lambda x: x[0], reverse=True)
    rows = []
    for score, school in scored[:5]:
        rows.append(
            f"학교명: {school['학교명']}\n"
            f"지역: {school['지역']}\n"
            f"학교유형: {school['학교유형']}\n"
            f"매칭과목수: {score}/{len(subject_list)}개"
        )
    return "\n---\n".join(rows)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=8080)
