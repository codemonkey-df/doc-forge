import { test, describe } from "node:test";
import assert from "node:assert";
import { spawnSync } from "node:child_process";
import { existsSync, unlinkSync, writeFileSync } from "node:fs";

const CONVERTER = "converter.js";
const FIXTURES = "tests/fixtures/";

function runConverter(jsonPath, docxPath) {
  const result = spawnSync("node", [CONVERTER, jsonPath, docxPath], {
    encoding: "utf-8",
  });
  return result;
}

describe("converter.js", () => {
  test("converts valid JSON to DOCX", () => {
    const jsonPath = FIXTURES + "structure.json";
    const docxPath = FIXTURES + "output.docx";

    // Clean up previous output
    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }

    const result = runConverter(jsonPath, docxPath);

    assert.strictEqual(result.status, 0, result.stderr);
    assert.ok(existsSync(docxPath), "DOCX file should be created");

    // Clean up
    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }
  });

  test("handles empty sections array", () => {
    const jsonPath = FIXTURES + "empty_sections.json";
    const docxPath = FIXTURES + "empty_output.docx";

    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }

    const result = runConverter(jsonPath, docxPath);

    assert.strictEqual(result.status, 0, result.stderr);
    assert.ok(existsSync(docxPath), "DOCX file should be created with empty sections");

    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }
  });

  test("handles empty code block", () => {
    const jsonPath = FIXTURES + "empty_code.json";
    const docxPath = FIXTURES + "empty_code_output.docx";

    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }

    const result = runConverter(jsonPath, docxPath);

    assert.strictEqual(result.status, 0, result.stderr);
    assert.ok(existsSync(docxPath), "DOCX file should be created with empty code block");

    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }
  });

  test("exits with error for invalid JSON", () => {
    const jsonPath = FIXTURES + "invalid.json";
    const docxPath = FIXTURES + "error_output.docx";

    // Create invalid JSON file
    writeFileSync(jsonPath, "{ invalid json }");

    const result = runConverter(jsonPath, docxPath);

    assert.notStrictEqual(result.status, 0, "Should exit with error for invalid JSON");
    assert.ok(result.stderr.includes("Failed to parse JSON"), "Should show parse error");

    // Clean up
    if (existsSync(jsonPath)) {
      unlinkSync(jsonPath);
    }
    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }
  });

  test("exits with error for missing image", () => {
    const jsonPath = FIXTURES + "missing_image.json";
    const docxPath = FIXTURES + "missing_image_output.docx";

    writeFileSync(jsonPath, JSON.stringify({
      metadata: { title: "Test", author: "Test", created: "2026-02-16T10:00:00Z" },
      sections: [{ type: "image", path: "/nonexistent/image.png" }]
    }));

    const result = runConverter(jsonPath, docxPath);

    assert.notStrictEqual(result.status, 0, "Should exit with error for missing image");
    assert.ok(result.stderr.includes("Image file not found"), "Should show missing image error");

    // Clean up
    if (existsSync(jsonPath)) {
      unlinkSync(jsonPath);
    }
    if (existsSync(docxPath)) {
      unlinkSync(docxPath);
    }
  });

  test("exits with error when missing arguments", () => {
    const result = spawnSync("node", [CONVERTER], {
      encoding: "utf-8",
    });

    assert.notStrictEqual(result.status, 0, "Should exit with error for missing arguments");
    assert.ok(result.stderr.includes("Usage:"), "Should show usage message");
  });
});
