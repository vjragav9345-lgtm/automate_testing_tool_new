# 🏆 Sportzia Preprod Automation & Testing Guide
**Target Site:** `https://sportzia-preprod.kovaionplay.com`

This guide explains how to perform testing scenarios (Search, Filters, Price filtering, Registration Status, Sorting, Duplicates, and Counting) using the automation test tool.

---

## 📊 Summary of Implemented Actions

| Action Category | Action Name | Purpose on Sportzia | Implementation Status |
|---|---|---|---|
| **Navigation & Flow** | `navigate` | Open URLs (`/feed`, `/events`, etc.) | ✅ Already Implemented |
| **Interaction** | `click` | Click buttons, event cards, tabs | ✅ Already Implemented |
| **Input & Form** | `fill` | Type search queries, form inputs | ✅ Already Implemented |
| **Dropdown** | `select` | Select options from dropdown lists | ✅ Already Implemented |
| **Visual Proof** | `screenshot` | Capture visual evidence image | ✅ Already Implemented |
| **Text Check** | `validate` | Assert exact text appears on page | ✅ Already Implemented |
| **Conditional Click**| `click_if_exists` | Click optional popups or banners if visible | ✅ Already Implemented |
| **Data Extraction** | `capture_value` | Read text from page & store in variable | ✅ Already Implemented |
| **Text Comparison** | `compare_value` | Compare text vs stored variable | ✅ Already Implemented |
| **Element State** | `validate_element` | Check disabled/enabled/present/visible | 🆕 Newly Implemented |
| **Element Counting**| `count_elements` | Count active/inactive events or cards | 🆕 Newly Implemented |
| **Count Comparison**| `compare_counts` | Compare counts (e.g. Active + Inactive == Total)| 🆕 Newly Implemented |
| **Terminal Report** | `count_summary` | Print formatted count table at script end | 🆕 Newly Implemented |
| **Checkbox/Radio** | `check_checked` | Verify filter checkboxes selection state | 🆕 Newly Implemented |
| **Value Bounds** | `validate_value_range`| Assert event prices are within ₹200–₹500 | 🆕 Newly Implemented |
| **Duplicate Audit** | `detect_duplicates` | Verify search results have no duplicate titles | 🆕 Newly Implemented |

---

## 🛠️ Where and How to Put JSON Code in Recording Files

All test actions live inside the `"actions": [ ... ]` array in your session JSON files located at:
`d:\new_test\storage\recordings\session_YYYYMMDD_HHMMSS.json`

### General Structure of a Session JSON:
```json
{
  "name": "session_20260903_151100",
  "start_url": "https://sportzia-preprod.kovaionplay.com/events",
  "actions": [
    { "action_type": "navigate", "page_url": "https://sportzia-preprod.kovaionplay.com/events" },
    
    // 👈 INSERT YOUR CUSTOM VALIDATION / COUNT / FILTER ACTIONS HERE
    
    { "action_type": "screenshot", "label": "final_state" }
  ]
}
```

---

## 📖 Complete Action Catalog & Examples

---

### 1. `count_elements` (🆕 Newly Implemented)
* **How to Use**: Count how many events are listed on Sportzia based on registration status ("Register Now" vs "Registration Closed") or category.
* **Where to Place**: Insert **AFTER** navigating to the `/events` page or **AFTER** applying a search/filter.
* **Exact JSON Code**:
```json
{
  "action_type": "count_elements",
  "count_as": "register_open_events",
  "min_count": 1,
  "locator_profile": {
    "text": "Register",
    "xpath": "//button[contains(text(), 'Register') or contains(text(), 'Register Now')]"
  }
},
{
  "action_type": "count_elements",
  "count_as": "registration_closed_events",
  "locator_profile": {
    "text": "Registration Closed",
    "xpath": "//*[contains(text(), 'Registration Closed') or contains(text(), 'Closed')]"
  }
}
```

---

### 2. `validate_element` (🆕 Newly Implemented)
* **How to Use**: Verify if a button/badge on Sportzia is disabled, enabled, visible, or absent (e.g. verifying that a "Registration Closed" button is disabled).
* **Where to Place**: Insert right after encountering an event card or modal.
* **Exact JSON Code**:
```json
{
  "action_type": "validate_element",
  "check": "disabled",
  "locator_profile": {
    "text": "Registration Closed",
    "xpath": "//button[contains(text(), 'Registration Closed')]"
  }
}
```

---

### 3. `check_checked` (🆕 Newly Implemented)
* **How to Use**: Test Sportzia filter checkboxes (Location, Sport Category, Price filters) to verify if they are selected/unselected.
* **Where to Place**: Insert **AFTER** clicking a filter checkbox.
* **Exact JSON Code**:
```json
{
  "action_type": "check_checked",
  "expected_state": "checked",
  "locator_profile": {
    "css_path": "input[type='checkbox']#filter-marathon",
    "xpath": "//input[@id='filter-marathon']"
  }
}
```

---

### 4. `validate_value_range` (🆕 Newly Implemented)
* **How to Use**: Validate price range filters (e.g., verifying that filtered event prices fall between ₹200 and ₹500, or below ₹200).
* **Where to Place**: Insert **AFTER** applying a price range filter.
* **Exact JSON Code**:
```json
{
  "action_type": "validate_value_range",
  "min_value": 200,
  "max_value": 500,
  "locator_profile": {
    "css_path": ".event-card .event-price",
    "xpath": "//span[contains(@class, 'price')]"
  }
}
```

---

### 5. `detect_duplicates` (🆕 Newly Implemented)
* **How to Use**: Ensure Sportzia event listing or search results do not contain duplicate event titles.
* **Where to Place**: Insert **AFTER** loading the events list or performing a search.
* **Exact JSON Code**:
```json
{
  "action_type": "detect_duplicates",
  "detect_by": "text",
  "locator_profile": {
    "css_path": ".event-card-title",
    "xpath": "//h3[contains(@class, 'event-title')]"
  }
}
```

---

### 6. `compare_counts` (🆕 Newly Implemented)
* **How to Use**: Compare two captured counts (e.g., verifying `filtered_events` <= `total_events`).
* **Where to Place**: Insert **AFTER** capturing counts for both initial and filtered lists.
* **Exact JSON Code**:
```json
{
  "action_type": "compare_counts",
  "count_a": "filtered_events",
  "count_b": "total_events",
  "operator": "lte"
}
```

---

### 7. `count_summary` (🆕 Newly Implemented)
* **How to Use**: Print a clean summary table of all recorded event counts in your terminal output.
* **Where to Place**: Insert at the **VERY END** of the `"actions"` array in your JSON session file.
* **Exact JSON Code**:
```json
{
  "action_type": "count_summary",
  "labels": ["total_events", "register_open_events", "registration_closed_events"]
}
```

---

### 8. Standard Actions (`fill`, `click`, `validate`, `navigate`)
* **How to Use**: Perform basic browser operations like searching for an event or navigating.
* **Exact JSON Code**:
```json
{
  "action_type": "fill",
  "value": "Marathon",
  "locator_profile": {
    "css_path": "input[placeholder*='Search']",
    "xpath": "//input[@placeholder='Search events']"
  }
},
{
  "action_type": "click",
  "locator_profile": {
    "text": "Search",
    "xpath": "//button[contains(text(), 'Search')]"
  }
},
{
  "action_type": "validate",
  "value": "Marathon"
}
```

---

## ⚡ Step-by-Step Execution Command

To run any session JSON file containing these actions, use the terminal command:

```powershell
python generator/script_generator.py storage/recordings/session_20260903_151100.json
```
