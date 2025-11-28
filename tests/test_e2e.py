"""
End-to-End Browser tests for ChatOS.

Tests user flows using Playwright browser automation.
Requires: pip install playwright && playwright install
"""

import pytest
import asyncio
from typing import Generator
from unittest.mock import patch

# Try to import Playwright
try:
    from playwright.sync_api import Page, expect, sync_playwright
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Skip all tests if Playwright not installed
pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="Playwright not installed. Run: pip install playwright && playwright install"
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def browser():
    """Launch browser for tests."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def base_url():
    """Base URL for ChatOS."""
    return "http://localhost:8000"


def server_available(url: str) -> bool:
    """Check if server is available."""
    try:
        import httpx
        resp = httpx.get(f"{url}/api/health", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


requires_server = pytest.mark.skipif(
    not server_available("http://localhost:8000"),
    reason="ChatOS server not running at localhost:8000"
)


# =============================================================================
# Main Page Tests
# =============================================================================

class TestMainPage:
    """Tests for the main chat page."""

    @requires_server
    def test_page_loads(self, page: "Page", base_url: str):
        """Main page should load successfully."""
        page.goto(base_url)
        
        # Should have title
        expect(page).to_have_title("ChatOS")

    @requires_server
    def test_chat_input_exists(self, page: "Page", base_url: str):
        """Chat input should be visible and accessible."""
        page.goto(base_url)
        
        # Find message input
        input_el = page.locator("#message-input")
        expect(input_el).to_be_visible()
        expect(input_el).to_have_attribute("placeholder")

    @requires_server
    def test_send_button_exists(self, page: "Page", base_url: str):
        """Send button should be visible."""
        page.goto(base_url)
        
        # Find send button
        send_btn = page.locator("#send-button")
        expect(send_btn).to_be_visible()

    @requires_server
    def test_sidebar_visible(self, page: "Page", base_url: str):
        """Sidebar should be visible."""
        page.goto(base_url)
        
        sidebar = page.locator(".sidebar")
        expect(sidebar).to_be_visible()

    @requires_server
    def test_command_buttons_exist(self, page: "Page", base_url: str):
        """Command buttons should exist in sidebar."""
        page.goto(base_url)
        
        # Check for command buttons
        commands = ["/code", "/research", "/deepthinking", "/swarm"]
        for cmd in commands:
            btn = page.locator(f"button:has-text('{cmd}')")
            expect(btn).to_be_visible()


# =============================================================================
# Chat Interaction Tests
# =============================================================================

class TestChatInteraction:
    """Tests for chat interactions."""

    @requires_server
    def test_type_message(self, page: "Page", base_url: str):
        """Should be able to type in message input."""
        page.goto(base_url)
        
        input_el = page.locator("#message-input")
        input_el.fill("Test message")
        
        expect(input_el).to_have_value("Test message")

    @requires_server
    def test_command_insertion(self, page: "Page", base_url: str):
        """Clicking command button should insert command."""
        page.goto(base_url)
        
        # Click /code button
        page.locator("button:has-text('/code')").click()
        
        # Check input has command
        input_el = page.locator("#message-input")
        expect(input_el).to_have_value("/code ")

    @requires_server
    def test_clear_button(self, page: "Page", base_url: str):
        """Clear button should reset chat."""
        page.goto(base_url)
        
        # Type something first
        input_el = page.locator("#message-input")
        input_el.fill("Test")
        
        # Click clear button if exists
        clear_btn = page.locator("button:has-text('Clear')")
        if clear_btn.is_visible():
            clear_btn.click()
            
            # Input should be empty after clear
            expect(input_el).to_have_value("")


# =============================================================================
# Settings Page Tests
# =============================================================================

class TestSettingsPage:
    """Tests for the settings page."""

    @requires_server
    def test_settings_page_loads(self, page: "Page", base_url: str):
        """Settings page should load."""
        page.goto(f"{base_url}/settings")
        
        # Should have settings content
        expect(page.locator("h1:has-text('Settings')").or_(
            page.locator("h2:has-text('Provider')")
        )).to_be_visible()

    @requires_server
    def test_providers_listed(self, page: "Page", base_url: str):
        """Provider list should be visible."""
        page.goto(f"{base_url}/settings")
        
        # Should show Ollama provider
        expect(page.locator("text=Ollama")).to_be_visible()

    @requires_server
    def test_settings_navigation_from_sidebar(self, page: "Page", base_url: str):
        """Should navigate to settings from sidebar."""
        page.goto(base_url)
        
        # Click settings link
        page.locator("a[href='/settings']").first.click()
        
        # Should be on settings page
        expect(page).to_have_url(f"{base_url}/settings")


# =============================================================================
# Projects Page Tests
# =============================================================================

class TestProjectsPage:
    """Tests for the projects page."""

    @requires_server
    def test_projects_page_loads(self, page: "Page", base_url: str):
        """Projects page should load."""
        page.goto(f"{base_url}/projects")
        
        # Should have projects content
        expect(page.locator("text=Projects").or_(
            page.locator("h1:has-text('Project')")
        ).first).to_be_visible()

    @requires_server
    def test_project_templates_visible(self, page: "Page", base_url: str):
        """Project templates should be visible."""
        page.goto(f"{base_url}/projects")
        
        # Should show at least one template
        templates = page.locator(".template-card, .project-template")
        expect(templates.first).to_be_visible()

    @requires_server
    def test_create_project_modal(self, page: "Page", base_url: str):
        """Should open create project modal."""
        page.goto(f"{base_url}/projects")
        
        # Click a template card
        template = page.locator(".template-card, .project-template").first
        template.click()
        
        # Modal should appear
        modal = page.locator(".modal, [role='dialog']")
        expect(modal).to_be_visible()


# =============================================================================
# Sandbox Page Tests
# =============================================================================

class TestSandboxPage:
    """Tests for the sandbox page."""

    @requires_server
    def test_sandbox_page_loads(self, page: "Page", base_url: str):
        """Sandbox page should load."""
        page.goto(f"{base_url}/sandbox")
        
        # Should have sandbox content
        expect(page.locator("text=Sandbox").or_(
            page.locator(".code-editor")
        ).first).to_be_visible()

    @requires_server
    def test_code_editor_visible(self, page: "Page", base_url: str):
        """Code editor should be visible."""
        page.goto(f"{base_url}/sandbox")
        
        # Should have textarea or code editor
        editor = page.locator("textarea, .code-editor, #editor")
        expect(editor.first).to_be_visible()

    @requires_server
    def test_run_button_visible(self, page: "Page", base_url: str):
        """Run button should be visible."""
        page.goto(f"{base_url}/sandbox")
        
        run_btn = page.locator("button:has-text('Run')")
        expect(run_btn).to_be_visible()


# =============================================================================
# Accessibility Tests
# =============================================================================

class TestAccessibility:
    """Tests for accessibility features."""

    @requires_server
    def test_input_has_placeholder(self, page: "Page", base_url: str):
        """Chat input should have placeholder text."""
        page.goto(base_url)
        
        input_el = page.locator("#message-input")
        placeholder = input_el.get_attribute("placeholder")
        
        assert placeholder is not None
        assert len(placeholder) > 0

    @requires_server
    def test_buttons_have_titles(self, page: "Page", base_url: str):
        """Buttons should have title or aria-label."""
        page.goto(base_url)
        
        # Send button should be accessible
        send_btn = page.locator("#send-button")
        title = send_btn.get_attribute("title")
        aria_label = send_btn.get_attribute("aria-label")
        
        # Should have at least one
        assert title or aria_label or send_btn.inner_text()

    @requires_server
    def test_links_have_href(self, page: "Page", base_url: str):
        """Navigation links should have href."""
        page.goto(base_url)
        
        nav_links = page.locator(".sidebar a")
        count = nav_links.count()
        
        for i in range(count):
            link = nav_links.nth(i)
            href = link.get_attribute("href")
            assert href is not None

    @requires_server
    def test_keyboard_navigation(self, page: "Page", base_url: str):
        """Should be able to navigate with keyboard."""
        page.goto(base_url)
        
        # Focus input
        input_el = page.locator("#message-input")
        input_el.focus()
        
        # Type and press Enter
        input_el.type("Test")
        
        # Input should have the text
        expect(input_el).to_have_value("Test")


# =============================================================================
# Responsive Design Tests
# =============================================================================

class TestResponsive:
    """Tests for responsive design."""

    @requires_server
    def test_mobile_viewport(self, page: "Page", base_url: str):
        """Should render correctly on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(base_url)
        
        # Chat container should still be visible
        chat = page.locator(".chat-container, #chat-container, main")
        expect(chat.first).to_be_visible()

    @requires_server
    def test_tablet_viewport(self, page: "Page", base_url: str):
        """Should render correctly on tablet viewport."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(base_url)
        
        # Main elements should be visible
        expect(page.locator("#message-input")).to_be_visible()

    @requires_server
    def test_desktop_viewport(self, page: "Page", base_url: str):
        """Should render correctly on desktop viewport."""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(base_url)
        
        # Sidebar should be visible on desktop
        sidebar = page.locator(".sidebar")
        expect(sidebar).to_be_visible()


# =============================================================================
# Navigation Tests
# =============================================================================

class TestNavigation:
    """Tests for navigation."""

    @requires_server
    def test_navigate_to_settings(self, page: "Page", base_url: str):
        """Should navigate to settings."""
        page.goto(base_url)
        page.goto(f"{base_url}/settings")
        
        expect(page).to_have_url(f"{base_url}/settings")

    @requires_server
    def test_navigate_to_projects(self, page: "Page", base_url: str):
        """Should navigate to projects."""
        page.goto(base_url)
        page.goto(f"{base_url}/projects")
        
        expect(page).to_have_url(f"{base_url}/projects")

    @requires_server
    def test_navigate_to_sandbox(self, page: "Page", base_url: str):
        """Should navigate to sandbox."""
        page.goto(base_url)
        page.goto(f"{base_url}/sandbox")
        
        expect(page).to_have_url(f"{base_url}/sandbox")

    @requires_server
    def test_navigate_back_home(self, page: "Page", base_url: str):
        """Should navigate back to home."""
        page.goto(f"{base_url}/settings")
        
        # Click home link or logo
        home_link = page.locator("a[href='/']").first
        home_link.click()
        
        expect(page).to_have_url(f"{base_url}/")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in UI."""

    @requires_server
    def test_404_page(self, page: "Page", base_url: str):
        """Should handle 404 gracefully."""
        response = page.goto(f"{base_url}/nonexistent-page")
        
        # Should either show 404 or redirect
        assert response.status in [200, 404]

    @requires_server
    def test_empty_message_not_sent(self, page: "Page", base_url: str):
        """Should not send empty message."""
        page.goto(base_url)
        
        # Click send without typing
        send_btn = page.locator("#send-button")
        
        # Get initial message count
        initial_messages = page.locator(".message, .chat-message").count()
        
        send_btn.click()
        
        # Wait a bit
        page.wait_for_timeout(500)
        
        # Message count should not have increased
        current_messages = page.locator(".message, .chat-message").count()
        assert current_messages == initial_messages

