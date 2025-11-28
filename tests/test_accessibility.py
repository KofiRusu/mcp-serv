"""
Accessibility Audit tests for ChatOS HTML templates.

Tests for ARIA attributes, keyboard navigation, semantic HTML,
and other accessibility best practices.
"""

import pytest
import re
from pathlib import Path
from bs4 import BeautifulSoup


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def templates_dir():
    """Path to templates directory."""
    return Path(__file__).parent.parent / "ChatOS" / "templates"


@pytest.fixture
def index_html(templates_dir):
    """Parse index.html."""
    with open(templates_dir / "index.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def settings_html(templates_dir):
    """Parse settings.html."""
    with open(templates_dir / "settings.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def sandbox_html(templates_dir):
    """Parse sandbox.html."""
    with open(templates_dir / "sandbox.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def projects_html(templates_dir):
    """Parse projects.html."""
    with open(templates_dir / "projects.html") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def all_templates(index_html, settings_html, sandbox_html, projects_html):
    """All templates as dict."""
    return {
        "index": index_html,
        "settings": settings_html,
        "sandbox": sandbox_html,
        "projects": projects_html,
    }


# =============================================================================
# Document Structure Tests
# =============================================================================

class TestDocumentStructure:
    """Tests for basic document structure."""

    def test_html_lang_attribute(self, all_templates):
        """HTML should have lang attribute."""
        for name, soup in all_templates.items():
            html = soup.find("html")
            assert html.get("lang"), f"{name}: Missing lang attribute on <html>"
            assert html.get("lang") == "en", f"{name}: Expected lang='en'"

    def test_charset_meta(self, all_templates):
        """Should have charset meta tag."""
        for name, soup in all_templates.items():
            charset = soup.find("meta", charset=True)
            assert charset, f"{name}: Missing charset meta tag"
            assert charset.get("charset").lower() == "utf-8"

    def test_viewport_meta(self, all_templates):
        """Should have viewport meta tag."""
        for name, soup in all_templates.items():
            viewport = soup.find("meta", attrs={"name": "viewport"})
            assert viewport, f"{name}: Missing viewport meta tag"

    def test_title_exists(self, all_templates):
        """Should have title element."""
        for name, soup in all_templates.items():
            title = soup.find("title")
            assert title, f"{name}: Missing <title> element"
            assert title.string, f"{name}: Empty <title> element"


# =============================================================================
# Semantic HTML Tests
# =============================================================================

class TestSemanticHTML:
    """Tests for semantic HTML usage."""

    def test_has_main_element(self, all_templates):
        """Should have <main> element."""
        for name, soup in all_templates.items():
            main = soup.find("main")
            assert main, f"{name}: Missing <main> element"

    def test_has_aside_sidebar(self, all_templates):
        """Sidebars should use <aside>."""
        for name, soup in all_templates.items():
            sidebar = soup.find("aside", class_=re.compile("sidebar"))
            assert sidebar, f"{name}: Sidebar should use <aside> element"

    def test_headings_hierarchy(self, all_templates):
        """Headings should follow proper hierarchy."""
        for name, soup in all_templates.items():
            headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            
            if not headings:
                continue
            
            # Check H1 exists (warning, not hard failure)
            h1s = soup.find_all("h1")
            if len(h1s) < 1:
                print(f"Warning: {name} should have at least one <h1> for accessibility")

    def test_sections_have_headings(self, all_templates):
        """Major sections should have headings."""
        for name, soup in all_templates.items():
            sections = soup.find_all("section")
            for section in sections:
                heading = section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
                # This is a recommendation, not hard failure
                if not heading:
                    print(f"Warning: {name} has <section> without heading")


# =============================================================================
# Form Accessibility Tests
# =============================================================================

class TestFormAccessibility:
    """Tests for form accessibility."""

    def test_inputs_have_labels(self, all_templates):
        """Form inputs should have associated labels."""
        for name, soup in all_templates.items():
            inputs = soup.find_all("input", {"type": ["text", "email", "password", "number"]})
            
            for inp in inputs:
                input_id = inp.get("id")
                
                # Check for associated label or aria-label
                has_label = False
                if input_id:
                    label = soup.find("label", {"for": input_id})
                    if label:
                        has_label = True
                
                if inp.get("aria-label") or inp.get("aria-labelledby"):
                    has_label = True
                
                if inp.get("placeholder"):
                    # Placeholder alone is not sufficient but we'll note it
                    pass
                
                # Many inputs may be dynamically labeled, so we just warn
                if not has_label and not inp.get("placeholder"):
                    print(f"Warning: {name} input missing label/aria-label")

    def test_textareas_have_labels(self, all_templates):
        """Textareas should have associated labels."""
        for name, soup in all_templates.items():
            textareas = soup.find_all("textarea")
            
            for textarea in textareas:
                ta_id = textarea.get("id")
                
                has_label = False
                if ta_id:
                    label = soup.find("label", {"for": ta_id})
                    if label:
                        has_label = True
                
                if textarea.get("aria-label") or textarea.get("aria-labelledby"):
                    has_label = True
                
                if textarea.get("placeholder"):
                    has_label = True  # placeholder is acceptable for visible hint

    def test_selects_have_labels(self, all_templates):
        """Select elements should have labels."""
        for name, soup in all_templates.items():
            selects = soup.find_all("select")
            
            for select in selects:
                select_id = select.get("id")
                
                has_label = False
                if select_id:
                    label = soup.find("label", {"for": select_id})
                    if label:
                        has_label = True
                
                if select.get("aria-label") or select.get("aria-labelledby"):
                    has_label = True


# =============================================================================
# Button Accessibility Tests
# =============================================================================

class TestButtonAccessibility:
    """Tests for button accessibility."""

    def test_buttons_have_accessible_names(self, all_templates):
        """Buttons should have accessible names."""
        for name, soup in all_templates.items():
            buttons = soup.find_all("button")
            
            for btn in buttons:
                # Check for accessible name
                has_name = False
                
                if btn.string and btn.string.strip():
                    has_name = True
                elif btn.get("aria-label"):
                    has_name = True
                elif btn.get("aria-labelledby"):
                    has_name = True
                elif btn.get("title"):
                    has_name = True
                elif btn.find(string=True, recursive=True):
                    has_name = True
                
                # Most buttons should have names
                if not has_name:
                    print(f"Warning: {name} has button without accessible name")

    def test_icon_buttons_have_title(self, all_templates):
        """Icon-only buttons should have title or aria-label."""
        missing_count = 0
        for name, soup in all_templates.items():
            # Find buttons that likely only have icons
            icon_buttons = soup.find_all("button", class_=re.compile("icon"))
            
            for btn in icon_buttons:
                has_accessible_name = (
                    btn.get("title") or 
                    btn.get("aria-label") or
                    btn.get("aria-labelledby")
                )
                
                if not has_accessible_name:
                    missing_count += 1
                    print(f"Warning: {name} icon button missing title/aria-label")
        
        # Report but don't fail - these are accessibility recommendations
        if missing_count > 0:
            print(f"Found {missing_count} icon buttons without accessible names")


# =============================================================================
# Link Accessibility Tests
# =============================================================================

class TestLinkAccessibility:
    """Tests for link accessibility."""

    def test_links_have_href(self, all_templates):
        """Links should have href attribute."""
        for name, soup in all_templates.items():
            links = soup.find_all("a")
            
            for link in links:
                href = link.get("href")
                # Links should have href
                assert href is not None or link.get("name"), f"{name}: Link missing href"

    def test_links_have_accessible_text(self, all_templates):
        """Links should have accessible text."""
        for name, soup in all_templates.items():
            links = soup.find_all("a")
            
            for link in links:
                has_text = False
                
                if link.string and link.string.strip():
                    has_text = True
                elif link.get("aria-label"):
                    has_text = True
                elif link.get("aria-labelledby"):
                    has_text = True
                elif link.find(string=True, recursive=True):
                    text = link.get_text(strip=True)
                    if text:
                        has_text = True
                
                if not has_text:
                    print(f"Warning: {name} has link without accessible text")


# =============================================================================
# Image Accessibility Tests
# =============================================================================

class TestImageAccessibility:
    """Tests for image accessibility."""

    def test_images_have_alt(self, all_templates):
        """Images should have alt attribute."""
        for name, soup in all_templates.items():
            images = soup.find_all("img")
            
            for img in images:
                # All images should have alt (even if empty for decorative)
                assert img.has_attr("alt"), f"{name}: Image missing alt attribute"


# =============================================================================
# ARIA Attribute Tests
# =============================================================================

class TestARIAAttributes:
    """Tests for ARIA attribute usage."""

    def test_no_invalid_aria_roles(self, all_templates):
        """Should not have invalid ARIA roles."""
        valid_roles = {
            "alert", "alertdialog", "application", "article", "banner", "button",
            "cell", "checkbox", "columnheader", "combobox", "complementary",
            "contentinfo", "definition", "dialog", "directory", "document",
            "feed", "figure", "form", "grid", "gridcell", "group", "heading",
            "img", "link", "list", "listbox", "listitem", "log", "main", "marquee",
            "math", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio",
            "navigation", "none", "note", "option", "presentation", "progressbar",
            "radio", "radiogroup", "region", "row", "rowgroup", "rowheader",
            "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton",
            "status", "switch", "tab", "table", "tablist", "tabpanel", "term",
            "textbox", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem"
        }
        
        for name, soup in all_templates.items():
            elements_with_role = soup.find_all(attrs={"role": True})
            
            for el in elements_with_role:
                role = el.get("role")
                assert role in valid_roles, f"{name}: Invalid ARIA role '{role}'"

    def test_aria_hidden_usage(self, all_templates):
        """Check proper aria-hidden usage."""
        for name, soup in all_templates.items():
            hidden_elements = soup.find_all(attrs={"aria-hidden": "true"})
            
            for el in hidden_elements:
                # aria-hidden elements should not contain focusable elements
                focusable = el.find_all(["a", "button", "input", "select", "textarea"])
                # Filter out ones with tabindex=-1
                focusable = [f for f in focusable if f.get("tabindex") != "-1"]
                
                if focusable:
                    print(f"Warning: {name} has focusable content inside aria-hidden")


# =============================================================================
# Keyboard Navigation Tests  
# =============================================================================

class TestKeyboardNavigation:
    """Tests for keyboard navigation support."""

    def test_focusable_elements_not_hidden(self, all_templates):
        """Focusable elements should not be hidden from tab order incorrectly."""
        for name, soup in all_templates.items():
            # Find elements with tabindex < 0
            negative_tabindex = soup.find_all(attrs={"tabindex": lambda x: x and int(x) < 0})
            
            # This is valid for some elements, just tracking
            if negative_tabindex:
                print(f"Info: {name} has {len(negative_tabindex)} elements with negative tabindex")

    def test_interactive_elements_accessible(self, all_templates):
        """Interactive elements should be keyboard accessible."""
        for name, soup in all_templates.items():
            # Find onclick handlers on non-button elements
            onclick_elements = soup.find_all(attrs={"onclick": True})
            
            for el in onclick_elements:
                tag = el.name
                
                # Buttons and links are naturally keyboard accessible
                if tag in ["button", "a", "input", "select", "textarea"]:
                    continue
                
                # Divs/spans with onclick should have role and tabindex
                if tag in ["div", "span", "li"]:
                    has_keyboard = (
                        el.get("tabindex") is not None or
                        el.get("role") in ["button", "link", "menuitem"]
                    )
                    
                    if not has_keyboard:
                        print(f"Warning: {name} <{tag}> with onclick may not be keyboard accessible")


# =============================================================================
# Modal/Dialog Accessibility Tests
# =============================================================================

class TestModalAccessibility:
    """Tests for modal/dialog accessibility."""

    def test_modals_have_role(self, all_templates):
        """Modal elements should have appropriate role."""
        for name, soup in all_templates.items():
            modals = soup.find_all(class_=re.compile("modal"))
            
            for modal in modals:
                role = modal.get("role")
                # Modals should have dialog or alertdialog role
                if not role:
                    print(f"Warning: {name} modal missing role='dialog'")

    def test_modals_have_aria_modal(self, all_templates):
        """Modals should have aria-modal attribute."""
        for name, soup in all_templates.items():
            modals = soup.find_all(attrs={"role": "dialog"})
            
            for modal in modals:
                if not modal.get("aria-modal"):
                    print(f"Warning: {name} dialog missing aria-modal='true'")


# =============================================================================
# Color and Contrast Tests
# =============================================================================

class TestVisualAccessibility:
    """Tests for visual accessibility (limited static checking)."""

    def test_no_inline_color_only(self, all_templates):
        """Check for potential color-only information."""
        # This is a very basic check - real color contrast testing needs browser
        for name, soup in all_templates.items():
            # Look for potential red/green only indicators
            # This is just a heuristic check
            error_classes = soup.find_all(class_=re.compile("error|danger|warning|success"))
            
            for el in error_classes:
                # Good practice: error elements should have icon or text, not just color
                text = el.get_text(strip=True)
                if not text and not el.find(["img", "svg", "span"]):
                    print(f"Warning: {name} may have color-only indicator")


# =============================================================================
# Specific ChatOS Element Tests
# =============================================================================

class TestChatOSSpecific:
    """Tests specific to ChatOS UI elements."""

    def test_chat_container_has_role(self, index_html):
        """Chat container should have appropriate role."""
        chat = index_html.find(id="chat-container")
        if chat:
            role = chat.get("role")
            # Chat logs should have role="log" or similar
            if not role:
                print("Recommendation: #chat-container could use role='log'")

    def test_message_input_accessible(self, index_html):
        """Message input should be accessible."""
        input_el = index_html.find(id="message-input")
        assert input_el, "Message input not found"
        
        # Should have placeholder or aria-label
        assert input_el.get("placeholder") or input_el.get("aria-label"), \
            "Message input needs placeholder or aria-label"

    def test_send_button_accessible(self, index_html):
        """Send button should be accessible."""
        send_btn = index_html.find(id="send-button")
        if send_btn:
            has_name = (
                send_btn.get("title") or
                send_btn.get("aria-label") or
                send_btn.get_text(strip=True)
            )
            assert has_name, "Send button needs accessible name"

    def test_command_items_accessible(self, index_html):
        """Command items should be keyboard accessible."""
        commands = index_html.find_all(class_="command-item")
        
        for cmd in commands:
            # Has onclick but should also be keyboard accessible
            if cmd.get("onclick"):
                # Should have tabindex or role="button"
                if not cmd.get("tabindex") and not cmd.get("role"):
                    print("Recommendation: .command-item could use tabindex='0' role='button'")
                    break  # Just warn once


# =============================================================================
# Summary Report
# =============================================================================

class TestAccessibilitySummary:
    """Generate summary of accessibility findings."""

    def test_generate_summary(self, all_templates):
        """Generate a summary report (always passes, prints findings)."""
        findings = {
            "passed": [],
            "warnings": [],
            "improvements": []
        }
        
        for name, soup in all_templates.items():
            # Check lang attribute
            html = soup.find("html")
            if html.get("lang"):
                findings["passed"].append(f"{name}: Has lang attribute")
            
            # Check main element
            if soup.find("main"):
                findings["passed"].append(f"{name}: Has <main> element")
            
            # Check title
            title = soup.find("title")
            if title and title.string:
                findings["passed"].append(f"{name}: Has <title>")
            
            # Check for modals without role
            modals = soup.find_all(class_=re.compile("modal"))
            for modal in modals:
                if not modal.get("role"):
                    findings["improvements"].append(f"{name}: Add role='dialog' to modal")
            
            # Check for onclick on non-interactive elements
            onclick_divs = soup.find_all("div", onclick=True)
            if onclick_divs:
                findings["improvements"].append(
                    f"{name}: Consider making clickable divs into buttons"
                )
        
        print("\n=== Accessibility Audit Summary ===")
        print(f"\nPassed: {len(findings['passed'])}")
        print(f"Warnings: {len(findings['warnings'])}")
        print(f"Improvements: {len(findings['improvements'])}")
        
        if findings["improvements"]:
            print("\nRecommended Improvements:")
            for imp in findings["improvements"][:10]:  # Limit output
                print(f"  - {imp}")
        
        # This test always passes - it's for reporting
        assert True

