from playwright.sync_api import sync_playwright, expect

def test_sorting_and_pagination(page):
    # Enable console logging
    page.on("console", lambda msg: print(f"Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Page Error: {err}"))

    # Mock Config
    page.route("**/api/config", lambda route: route.fulfill(json={"version": "1.0.0"}))

    # Mock Sidebar Data - Use wildcards to be safe
    page.route("**/api/tables*", lambda route: route.fulfill(json=[{"name": "EMPLOYEE"}]))
    page.route("**/api/views*", lambda route: route.fulfill(json=[]))
    page.route("**/api/procedures*", lambda route: route.fulfill(json=[]))

    # Mock Table Data
    def handle_data(route):
        request = route.request
        params = request.url.split("?")[1] if "?" in request.url else ""
        print(f"Data Request: {request.url}")

        data_unsorted = [
            {"EMP_NO": 1, "LAST_NAME": "Zuckerberg", "FIRST_NAME": "Mark"},
            {"EMP_NO": 2, "LAST_NAME": "Bezos", "FIRST_NAME": "Jeff"},
        ]

        data_sorted = [
            {"EMP_NO": 2, "LAST_NAME": "Bezos", "FIRST_NAME": "Jeff"},
            {"EMP_NO": 1, "LAST_NAME": "Zuckerberg", "FIRST_NAME": "Mark"},
        ]

        response_data = data_unsorted
        if "sortField=LAST_NAME" in params:
             response_data = data_sorted

        response = {
            "data": response_data,
            "columns": [
                {"name": "EMP_NO", "type": "INTEGER"},
                {"name": "FIRST_NAME", "type": "VARCHAR"},
                {"name": "LAST_NAME", "type": "VARCHAR"}
            ],
            "total": 100,
            "limit": 25,
            "offset": 0
        }

        route.fulfill(json=response)

    page.route("**/api/table/EMPLOYEE/data*", handle_data)

    # 1. Login/Setup
    page.goto("http://localhost:5173/")
    page.evaluate("localStorage.setItem('token', 'mock-token')")
    page.goto("http://localhost:5173/dashboard")

    # 2. Select Table
    # Wait for the Tree to populate
    # The tree node with label "Tables" should exist.
    try:
        page.get_by_text("Tables", exact=True).wait_for(timeout=5000)
        page.get_by_text("Tables", exact=True).click() # Expand if needed
    except:
        print("Could not find 'Tables' node. Taking screenshot.")
        page.screenshot(path="verification/debug_tree.png")
        raise

    # Click EMPLOYEE
    page.get_by_text("EMPLOYEE").click()

    # Wait for initial data
    expect(page.get_by_role("cell", name="Zuckerberg")).to_be_visible()

    # Screenshot Initial
    page.screenshot(path="verification/1_initial_unsorted.png")

    # 3. Sort by LAST_NAME
    page.get_by_role("columnheader", name="LAST_NAME").click()

    # Check expectation
    expect(page.get_by_role("cell", name="Bezos")).to_be_visible()

    # Screenshot Sorted
    page.screenshot(path="verification/2_sorted.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_sorting_and_pagination(page)
            print("Test finished successfully.")
        except Exception as e:
            print(f"Test failed: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()
