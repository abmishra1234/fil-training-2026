"""Generate the CabRoster manual testing pack from FastAPI's Swagger schema."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.main import app


OUT = Path(__file__).parent / "CabRoster_Manual_Testing.pdf"


def _op(method: str, path: str) -> dict:
    return app.openapi()["paths"][path][method.lower()]


def _response(method: str, path: str) -> str:
    responses = _op(method, path).get("responses", {})
    codes = [code for code in responses if code not in ("422", "default")]
    return ", ".join(codes) or "See Swagger"


def build():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape, portrait
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, KeepTogether)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=29, leading=34, textColor=colors.HexColor("#123B5D"), alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Deck", parent=styles["Normal"], fontSize=12, leading=17,
                              textColor=colors.HexColor("#526777")))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontSize=18, leading=22,
                              textColor=colors.HexColor("#123B5D"), spaceBefore=8, spaceAfter=9))
    styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading2"], fontSize=12, leading=15,
                              textColor=colors.HexColor("#145783"), spaceBefore=7, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=7.2, leading=9))
    styles.add(ParagraphStyle(name="CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
                              fontSize=7.2, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle(name="TestTitle", parent=styles["Heading3"], fontSize=10, leading=13,
                              textColor=colors.HexColor("#123B5D"), spaceBefore=8, spaceAfter=3))

    openapi = app.openapi()
    operations = [(m.upper(), p, v) for p, methods in openapi["paths"].items()
                  for m, v in methods.items() if m.lower() in {"get", "post", "patch", "delete"}]
    groups = [
        ("Health", ["/health"]),
        ("Authentication and profile", ["/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/me"]),
        ("Users and access", ["/api/v1/users"]),
        ("Cabs", ["/api/v1/cabs"]),
        ("Bookings", ["/api/v1/bookings"]),
        ("Trips and assignment", ["/api/v1/trips"]),
        ("Driver operations", ["/api/v1/driver/trips"]),
        ("Reports", ["/api/v1/reports"]),
    ]
    operation_groups = {
        "/health": ("Health", "Public"),
        "/api/v1/auth/register": ("Authentication", "Public"),
        "/api/v1/auth/login": ("Authentication", "Public"),
        "/api/v1/auth/me": ("Profile", "Bearer token"),
        "/api/v1/users": ("Users", "Admin"),
        "/api/v1/cabs": ("Cabs", "Admin"),
        "/api/v1/bookings": ("Bookings", "Employee for create/me; admin for all"),
        "/api/v1/trips": ("Trips", "Admin"),
        "/api/v1/driver/trips": ("Driver", "Driver"),
        "/api/v1/reports": ("Reports", "Admin"),
    }
    group_names = ["Health", "Authentication", "Profile", "Users", "Cabs", "Bookings", "Trips", "Driver", "Reports"]
    api_groups = {g: [] for g in group_names}
    for method, path, detail in operations:
        section, role = operation_groups.get(path, ("API", "See Swagger"))
        api_groups.setdefault(section, []).append((method, path, detail, role))

    def para(text, style="BodyText"):
        # Escape HTML except controlled <br/> in supplied content.
        from xml.sax.saxutils import escape
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])

    def header_footer(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize
        canvas.setStrokeColor(colors.HexColor("#D9E3EA"))
        canvas.line(doc.leftMargin, 13*mm, w-doc.rightMargin, 13*mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#617380"))
        canvas.drawString(doc.leftMargin, 8.5*mm, "CABROSTER  |  MANUAL API TEST PACK  |  INTERNAL")
        canvas.drawRightString(w-doc.rightMargin, 8.5*mm, f"Page {doc.page}")
        canvas.restoreState()

    class SwitchDoc(BaseDocTemplate):
        def __init__(self, filename):
            super().__init__(filename, pagesize=portrait(A4), rightMargin=17*mm, leftMargin=17*mm,
                             topMargin=17*mm, bottomMargin=19*mm, title="CabRoster Manual Testing Pack",
                             author="CabRoster QA")
            self.addPageTemplates(PageTemplate(id="portrait", frames=Frame(17*mm, 19*mm, A4[0]-34*mm,
                A4[1]-36*mm, id="pf"), onPage=header_footer))
            self.landscape = False
        def handle_pageBegin(self):
            self.pageTemplate = self.pageTemplates[1 if self.landscape else 0]
            super().handle_pageBegin()

    doc = SwitchDoc(str(OUT))
    doc.addPageTemplates(PageTemplate(id="landscape", pagesize=landscape(A4),
        frames=Frame(14*mm, 19*mm, landscape(A4)[0]-28*mm, landscape(A4)[1]-36*mm, id="lf"),
        onPage=header_footer))
    story = []
    story += [Spacer(1, 24*mm), para("CABROSTER", "CoverTitle"),
              para("Manual API testing pack", "Deck"), Spacer(1, 7*mm),
              para("Swagger-derived endpoint coverage with practical execution steps, expected outcomes, and space to record results.", "BodyText"),
              Spacer(1, 12*mm)]
    cover = [[para("API base path", "CellHead"), para("/api/v1", "Cell")],
             [para("Swagger UI", "CellHead"), para("/docs", "Cell")],
             [para("OpenAPI schema", "CellHead"), para("/openapi.json", "Cell")],
             [para("API operations", "CellHead"), para(str(len(operations)), "Cell")],
             [para("Prepared", "CellHead"), para(date.today().isoformat(), "Cell")]]
    t = Table(cover, colWidths=[43*mm, 100*mm], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0,0),(0,-1), colors.HexColor("#123B5D")),
                           ("BACKGROUND", (1,0),(1,-1), colors.HexColor("#F1F6F9")),
                           ("GRID", (0,0),(-1,-1), .4, colors.HexColor("#D3DEE5")),
                           ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                           ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
                           ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story += [t, Spacer(1, 9*mm), para("Execution record", "Subsection"),
              para("Environment: ____________________    Build/version: ____________________", "BodySmall"),
              para("Tester: _________________________    Execution date: __________________", "BodySmall"),
              para("Overall result:  □ Pass   □ Fail   □ Blocked", "BodySmall"), PageBreak()]

    story += [para("How to use this pack", "Section"),
              para("Run against a non-production environment. This quick start takes you from starting the API to a successful admin login. After that, use the Swagger operation inventory and test cases below. Record response status, relevant response fields, and any defect ID.", "BodyText"),
              para("Quick start: prepare the admin login", "Subsection")]
    quick_start = [
        "Open PowerShell or a terminal and change directory to the project folder that contains app/seed.py and requirements.txt.",
        "Activate the project's Python virtual environment if one is used. Otherwise, install dependencies with: python -m pip install -r requirements.txt.",
        "Check the database setting. The default is sqlite:///./cabroster.db, which means cabroster.db in the current project folder. If the API is configured with DATABASE_URL in .env or environment variables, keep that same setting for the next step.",
        "In this project folder and environment, run: python -m app.seed. Wait for 'Seed complete'. This creates the demo admin and demo data in the configured database. It is safe to rerun; existing accounts are not overwritten.",
        "Start the API from this same project folder and environment: python -m uvicorn app.main:app --reload. Keep this terminal running. If the app is already running, restart it after changing database settings.",
        "Open http://localhost:8000/docs. First open GET /health and click Try it out, then Execute. Confirm HTTP 200 with {\"status\":\"ok\"}; this verifies the server responds.",
        "Expand POST /api/v1/auth/login and click Try it out. This endpoint uses form fields, not a JSON request body. Enter username admin@cabroster.in and password Password1; leave other OAuth2 fields blank, then click Execute.",
        "Confirm HTTP 200 and copy the access_token from the response. The expected role is ADMIN. A 401 means the account was not found/active in this API database or the credentials differ; do not register an employee to fix it.",
        "Click the Swagger Authorize button. Paste the access token (or enter Bearer followed by one space and the token, depending on the dialog), authorize, and close. Try GET /api/v1/users to confirm an admin-only call succeeds (HTTP 200).",
        "If login still returns 401, stop the API, return to the project folder, confirm DATABASE_URL matches the API's configuration, rerun python -m app.seed using that same environment, restart the API, and retry. Do not use root.admin@acmecorp.in / Admin12345 here; those credentials are created only by pytest fixtures in an isolated test database.",
    ]
    for i, line in enumerate(quick_start, 1):
        story.append(para(f"{i}. {line}", "BodySmall"))
    story += [para("Reference setup", "Subsection")]
    setup = [
        "Seeded demo admin: username admin@cabroster.in, password Password1. Use this account for the running demo API after completing the quick-start seeding step.",
        "Test-suite admin: username root.admin@acmecorp.in, password Admin12345. This account is created by the pytest fixture in tests/conftest.py for its isolated test database; it may not exist in the running application database.",
        "Use an ADMIN account for fleet/user/trip/report operations, an EMPLOYEE account with home_address and zone for booking, and a DRIVER account for driver endpoints.",
        "Base API path is /api/v1. Root health is /health. Swagger UI is /docs. Registering employees is public; admin creates drivers and administrators.",
        "Typical service date example in the source test contract: Monday 2026-09-28. Dates must be weekdays, today through seven days ahead, subject to slot booking cutoffs. Confirm the environment date before using examples.",
        "Default schedule documented by configuration: PICKUP 06:30 IST, DROP 16:30 IST; booking cutoffs PICKUP previous day 21:00, DROP same day 14:00; cancellation cutoff 60 minutes before departure; driver start window opens 30 minutes before departure.",
        "Use unique emails, employee codes, registration numbers, and license numbers. Capture generated IDs for subsequent steps.",
    ]
    for i, line in enumerate(setup, 1):
        story.append(para(f"{i}. {line}", "BodySmall"))
    story += [para("Status and response guide", "Subsection"),
              para("Typical success: 200, creation: 201. Common errors include 401 unauthenticated/invalid credentials, 403 role not allowed, 404 missing or invisible resource, 409 duplicate/conflicting state, and 422 invalid input or business-rule violation. Exact response detail may vary; record response body.", "BodySmall"),
              para("Execution summary", "Subsection")]
    summary_rows = [[para("Area", "CellHead"), para("Operations", "CellHead"), para("Tester result", "CellHead"), para("Defect IDs / notes", "CellHead")]]
    for area in group_names:
        count = len(api_groups.get(area, []))
        if count:
            summary_rows.append([para(area,"Cell"),para(str(count),"Cell"),para("□ Pass  □ Fail  □ Blocked  □ N/R","Cell"),para("","Cell")])
    summary = Table(summary_rows, colWidths=[35*mm, 22*mm, 60*mm, 55*mm], repeatRows=1)
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123B5D")),
        ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#C9D5DD")),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F7F9")]),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story.append(summary)

    story += [PageBreak(), para("Swagger operation inventory", "Section"),
              para("The following operations are read from the running FastAPI app's OpenAPI document (the same schema served to Swagger UI).", "BodySmall")]
    doc.landscape = True
    inventory = [[para("Area", "CellHead"), para("Method", "CellHead"), para("Endpoint", "CellHead"),
                  para("Swagger summary", "CellHead"), para("Access", "CellHead"), para("Success", "CellHead")]]
    for method, path, detail in operations:
        area, role = operation_groups.get(path, ("API", "See Swagger"))
        inventory.append([para(area,"Cell"), para(method,"Cell"), para(path,"Cell"),
                          para(detail.get("summary", ""),"Cell"), para(role,"Cell"), para(_response(method,path),"Cell")])
    it = Table(inventory, colWidths=[29*mm,17*mm,74*mm,65*mm,42*mm,18*mm], repeatRows=1)
    it.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123B5D")),
       ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#C9D5DD")),("VALIGN",(0,0),(-1,-1),"TOP"),
       ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F7F9")]),
       ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
       ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    story.append(it)
    story.append(PageBreak())
    doc.landscape = False

    # Each case is concise and reproducible, with a manual result area.
    cases = [
      ("Health", [
       ("MT-HEA-01", "GET /health", "No token required.", "Send GET /health.", "200; body is {\"status\":\"ok\"}."),]),
      ("Authentication and profile", [
       ("MT-AUT-01", "POST /api/v1/auth/register", "No token. Use valid unique full_name, email, phone (10 digits starting 6–9), password (8–128 chars with a letter and digit), employee_code, home_address, zone.", "Submit registration JSON in Swagger.", "201; role EMPLOYEE, is_active true; response has no password/hash."),
       ("MT-AUT-02", "POST /api/v1/auth/register", "Reuse a registered email, then separately reuse an employee_code.", "Submit each duplicate registration.", "409 for each duplicate."),
       ("MT-AUT-03", "POST /api/v1/auth/login", "Registered active account credentials.", "Submit OAuth2 form fields username=email, password=password.", "200; access_token, token_type bearer, role. Authorize using token."),
       ("MT-AUT-04", "POST /api/v1/auth/login", "Use wrong password or inactive account.", "Submit login form.", "401; no access token."),
       ("MT-AUT-05", "GET /api/v1/auth/me", "No token, then valid employee token.", "Call endpoint both ways.", "401 without token; 200 with matching account profile and no password data."),
       ("MT-AUT-06", "PATCH /api/v1/auth/me", "Employee token; valid phone/address/zone. Also try malformed phone and null field.", "Update profile; inspect returned fields; submit invalid variants.", "200 and updated values; invalid/null inputs return 422."),
       ("MT-AUT-07", "PATCH /api/v1/auth/me", "Driver token.", "Try phone update, then home_address or zone update.", "Phone update succeeds; driver address/zone update returns 422."),]),
      ("Users and access", [
       ("MT-USR-01", "POST /api/v1/users", "Admin token. Create DRIVER with unique email, phone, password, license_no; also create ADMIN.", "Submit each valid body; repeat one email/license.", "201 with requested role; duplicate email/license returns 409."),
       ("MT-USR-02", "POST /api/v1/users", "No token and employee token.", "Attempt valid staff creation.", "401 without token; 403 for employee."),
       ("MT-USR-03", "GET /api/v1/users", "Admin token; seeded or created users.", "List; filter role, zone, is_active and q; try page=1,size=2 and page=2.", "200; items and total/page/size/pages reflect filters and pagination."),
       ("MT-USR-04", "GET /api/v1/users/{user_id}", "Admin token and a known user ID; then unknown ID.", "Fetch both IDs.", "200 for existing profile; 404 for missing ID."),
       ("MT-USR-05", "PATCH /api/v1/users/{user_id}/status", "Admin token and another user's ID.", "Set is_active false; verify user cannot log in; restore true. Try own admin ID.", "200 and state updates; self status change returns 409; inactive login returns 401."),]),
      ("Cabs", [
       ("MT-CAB-01", "POST /api/v1/cabs", "Admin token; unique valid registration such as KA01AB1234, model, capacity 1–12.", "Create cab with lowercase registration, then invalid registration/capacity and duplicate.", "201; registration normalized uppercase and active; invalid input 422; duplicate 409."),
       ("MT-CAB-02", "GET /api/v1/cabs", "Admin token.", "List; filter is_active/min_capacity/q; sort by capacity desc; request available_on with slot together.", "200 paginated results; filters/sort work. Supplying only one availability parameter returns 422."),
       ("MT-CAB-03", "GET /api/v1/cabs/{cab_id}", "Admin token and existing/nonexistent cab IDs.", "Fetch each.", "200 with cab fields; missing cab 404."),
       ("MT-CAB-04", "PATCH /api/v1/cabs/{cab_id}", "Admin token and cab ID; include a scheduled trip with assigned passengers for capacity check.", "Update model/active; lower capacity below assigned seats; submit invalid capacity/null.", "200 valid update; capacity conflict 409; invalid/null 422."),]),
      ("Bookings", [
       ("MT-BKG-01", "POST /api/v1/bookings", "Employee token with home_address and zone. Use eligible weekday within seven days before slot cutoff.", "Create PICKUP and DROP bookings on eligible dates; repeat same date/slot; try missing profile, weekend, past, beyond horizon, and after cutoff.", "201 BOOKED; zone/address copied from profile; trip null. Active duplicate 409; business-rule/profile/date/cutoff failures 422."),
       ("MT-BKG-02", "GET /api/v1/bookings/me", "Employee token with several bookings.", "List; filter slot/status/date_from/date_to; vary sort and pagination; use date_from later than date_to.", "200 only own records with pagination; invalid date range 422."),
       ("MT-BKG-03", "GET /api/v1/bookings", "Admin token; bookings created by multiple employees.", "List and filter date, slot, zone, status, employee_id, unassigned, q; paginate/sort.", "200 only matching records; employee call returns 403."),
       ("MT-BKG-04", "GET /api/v1/bookings/{booking_id}", "Employee token and own booking, another employee booking, and unknown ID; then admin token.", "Fetch each record.", "Owner/admin sees 200; employee cannot see another employee booking (404); missing ID 404."),
       ("MT-BKG-05", "PATCH /api/v1/bookings/{booking_id}/cancel", "Own BOOKED booking before cutoff; assigned booking on scheduled trip; then late/already-started/already-cancelled cases.", "Cancel each through Swagger.", "Valid cancellation 200 CANCELLED and detached from trip; late employee cancellation 422; invalid state or started trip 409."),]),
      ("Trips and assignment", [
       ("MT-TRP-01", "POST /api/v1/trips", "Admin token, active cab and active DRIVER. Eligible weekday/date, slot and zone.", "Create trip; repeat using same cab or driver/date/slot; try inactive cab, non-driver and missing references.", "201 SCHEDULED with 0 booked seats and capacity seats free. Duplicate cab/driver 409; inactive/wrong role 422; missing reference 404."),
       ("MT-TRP-02", "GET /api/v1/trips", "Admin token and trips with different dates/zones/statuses.", "Filter date/date range/slot/zone/status/driver/cab, sort and paginate; test reversed date range.", "200 matching page; reversed date range 422."),
       ("MT-TRP-03", "GET /api/v1/trips/{trip_id}", "Admin token and existing/nonexistent trip IDs.", "Fetch each.", "200 detail includes cab, driver and passenger list; missing trip 404."),
       ("MT-TRP-04", "POST /api/v1/trips/{trip_id}/bookings", "Admin token; scheduled trip and BOOKED bookings matching date, slot, zone.", "Assign one or more; then try duplicate IDs, mismatched zone/date/slot, already assigned, over capacity, and non-scheduled trip.", "200; passengers become ASSIGNED and seat counts update. Invalid/duplicate list 422; conflicts 409; missing booking 404; assignment is all-or-nothing."),
       ("MT-TRP-05", "DELETE /api/v1/trips/{trip_id}/bookings/{booking_id}", "Admin token; assigned booking on scheduled trip.", "Remove booking; try unrelated booking and started trip.", "Success response; booking returns BOOKED with null trip_id. Not-on-trip 404; non-scheduled 409."),
       ("MT-TRP-06", "PATCH /api/v1/trips/{trip_id}/cancel", "Admin token; scheduled trip with assigned passenger(s).", "Cancel trip; inspect trip and bookings; try cancellation again/after start.", "200 CANCELLED; eligible passengers are unassigned and BOOKED. Invalid status 409."),]),
      ("Driver operations", [
       ("MT-DRV-01", "GET /api/v1/driver/trips", "Driver token with assigned trips; include another driver's trip.", "List, filter date/status/slot and paginate.", "200 only own trips; other roles receive 403."),
       ("MT-DRV-02", "GET /api/v1/driver/trips/{trip_id}", "Driver token for own trip with passengers; then another driver's trip and missing ID.", "Fetch manifest.", "200 own manifest with passenger names/phones/addresses; others/missing return 404."),
       ("MT-DRV-03", "PATCH /api/v1/driver/trips/{trip_id}/start", "Own scheduled trip; use eligible travel-date time inside 30-minute pre-departure window.", "Start at valid time; also try too early, wrong date, wrong driver, and repeated start.", "200 IN_PROGRESS with started_at; too early/wrong date 422; inaccessible trip 404; invalid state 409."),
       ("MT-DRV-04", "PATCH /api/v1/driver/trips/{trip_id}/bookings/{booking_id}", "Own IN_PROGRESS trip with assigned passenger.", "Mark BOARDED; separately test NO_SHOW, unknown passenger and repeated marking.", "200 new status; missing passenger 404; repeat/non-progress status 409."),
       ("MT-DRV-05", "PATCH /api/v1/driver/trips/{trip_id}/complete", "Own IN_PROGRESS trip with boarded and still-assigned passengers.", "Complete and inspect trip/passengers; try before start and repeat.", "200 COMPLETED; BOARDED passengers become COMPLETED and unmarked ASSIGNED passengers become NO_SHOW. Wrong state 409."),]),
      ("Reports", [
       ("MT-RPT-01", "GET /api/v1/reports/daily-summary", "Admin token; known service date with bookings and trips across both slots.", "Request travel_date; compare totals with booking/trip lists. Try malformed date and non-admin.", "200 with each slot's booking status counts, trip count, capacity and utilisation_pct; malformed date 422; non-admin 403."),]),
    ]

    for section, entries in cases:
        story.append(para(section, "Section"))
        for tid, endpoint, pre, steps, expected in entries:
            block = [para(f"{tid}  |  {endpoint}", "TestTitle"),
                     para(f"<b>Preconditions:</b> {pre}", "BodySmall"),
                     para(f"<b>Steps:</b> {steps}", "BodySmall"),
                     para(f"<b>Expected:</b> {expected}", "BodySmall"),
                     para("<b>Actual status/body:</b> ______________________________________________________________", "BodySmall"),
                     para("<b>Result:</b> □ Pass  □ Fail  □ Blocked    <b>Defect ID / notes:</b> ______________________________", "BodySmall"),
                     Spacer(1, 2*mm)]
            story.append(KeepTogether(block))

    story += [PageBreak(), para("End-to-end scenario", "Section"),
      para("MT-E2E-01  |  Employee booking through completed journey", "TestTitle"),
      para("<b>Preconditions:</b> Active employee with complete address/zone, admin, driver and cab; eligible weekday within service horizon and booking window.", "BodySmall"),
      para("<b>Steps:</b> 1) Employee creates booking. 2) Admin creates trip for same date/slot/zone. 3) Admin assigns booking. 4) Driver retrieves manifest and starts in the allowed window. 5) Driver marks passenger BOARDED. 6) Driver completes trip. 7) Employee retrieves booking.", "BodySmall"),
      para("<b>Expected:</b> Booking transitions BOOKED → ASSIGNED → BOARDED → COMPLETED. Trip transitions SCHEDULED → IN_PROGRESS → COMPLETED. Final booking includes trip summary with cab registration and driver details.", "BodySmall"),
      para("<b>Actual status/body:</b> ______________________________________________________________", "BodySmall"),
      para("<b>Result:</b> □ Pass  □ Fail  □ Blocked    <b>Defect ID / notes:</b> ______________________________", "BodySmall"),
      Spacer(1,5*mm), para("Defect log", "Subsection")]
    defect_rows = [[para(x,"CellHead") for x in ["ID","Test case","Environment / build","Steps to reproduce","Expected vs actual","Severity","State"]]]
    defect_rows += [[para("","Cell") for _ in range(7)] for _ in range(6)]
    dt = Table(defect_rows, colWidths=[14*mm,23*mm,27*mm,48*mm,52*mm,19*mm,18*mm],
               rowHeights=[9*mm]+[15*mm]*6, repeatRows=1)
    dt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123B5D")),
        ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#AEBCC5")),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(dt)
    story += [Spacer(1,5*mm), para("Specification note", "Subsection"),
              para("Endpoint names, summaries, response models and declared success status codes in this pack are generated from the app's FastAPI OpenAPI schema. Business-rule expectations are derived from the repository implementation and test support data. Verify environment configuration where schedule settings or seed data differ.", "BodySmall")]

    doc.build(story)
    print(f"Generated {OUT} with {len(operations)} Swagger operations and {sum(len(x[1]) for x in cases)} manual test cases")


if __name__ == "__main__":
    build()
