from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    # Mock API responses
    page.route("**/api/config", lambda route: route.fulfill(json={"version": "1.2.3", "demo_mode": False}))

    # Mock data lists
    page.route("**/api/tables", lambda route: route.fulfill(json=[{"name": "EMPLOYEE"}, {"name": "DEPARTMENT"}]))
    page.route("**/api/views", lambda route: route.fulfill(json=[{"name": "PHONE_LIST"}]))
    page.route("**/api/procedures", lambda route: route.fulfill(json=[{"name": "GET_EMP_PROJ"}]))

    # Mock table data
    page.route("**/api/table/EMPLOYEE/data**", lambda route: route.fulfill(json={
        "data": [{"EMP_NO": 1, "FULL_NAME": "John Doe"}],
        "columns": [{"name": "EMP_NO", "type": "INTEGER"}, {"name": "FULL_NAME", "type": "VARCHAR"}],
        "total": 1,
        "limit": 100,
        "offset": 0
    }))

    page.add_init_script("localStorage.setItem('token', 'fake-token');")

    try:
        page.goto("http://localhost:5173/dashboard")
    except Exception as e:
        print(f"Nav error: {e}")

    page.wait_for_load_state("networkidle")

    # Verify Sidebar structure
    # Use exact match or filter to sidebar
    sidebar = page.locator(".w-64") # Sidebar class
    expect(sidebar.get_by_text("Tools")).to_be_visible()
    expect(sidebar.get_by_text("Tables")).to_be_visible()

    # Expand Tools (Click text)
    sidebar.get_by_text("Tools").click()

    # Check for SQL Editor
    expect(sidebar.get_by_text("SQL Editor")).to_be_visible()
    expect(sidebar.get_by_text("Database Info")).to_be_visible()

    # Expand Tables
    sidebar.get_by_text("Tables").click()
    expect(sidebar.get_by_text("EMPLOYEE")).to_be_visible()

    # Expand Views
    sidebar.get_by_text("Views").click()
    expect(sidebar.get_by_text("PHONE_LIST")).to_be_visible()

    # Expand Procedures
    sidebar.get_by_text("Procedures").click()
    expect(sidebar.get_by_text("GET_EMP_PROJ")).to_be_visible()

    # Select SQL Editor (Click label)
    sidebar.get_by_text("SQL Editor").click()

    # Verify Main Content
    expect(page.get_by_text("This tool is coming soon")).to_be_visible()
    # Check header
    expect(page.locator("header").get_by_text("SQL Editor")).to_be_visible()

    # Test Filter
    page.fill("input[placeholder='Search...']", "EMP")

    expect(sidebar.get_by_text("EMPLOYEE")).to_be_visible()
    expect(sidebar.get_by_text("GET_EMP_PROJ")).to_be_visible()
    expect(sidebar.get_by_text("PHONE_LIST")).not_to_be_visible()

    # Clear Filter
    page.fill("input[placeholder='Search...']", "")

    # Re-expand all if hidden
    # Using strict selectors

    if not sidebar.get_by_text("SQL Editor").is_visible():
        sidebar.get_by_text("Tools").click()

    if not sidebar.get_by_text("EMPLOYEE").is_visible():
        sidebar.get_by_text("Tables").click()

    if not sidebar.get_by_text("PHONE_LIST").is_visible():
        sidebar.get_by_text("Views").click()

    if not sidebar.get_by_text("GET_EMP_PROJ").is_visible():
        sidebar.get_by_text("Procedures").click()

    page.wait_for_timeout(500) # Wait for animation

    page.screenshot(path="verification/sidebar_complete.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
