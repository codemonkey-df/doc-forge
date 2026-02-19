/**
 * Tests for markdown parser.
 */

const {
  parseMarkdown,
  heading,
  paragraph,
  code,
  bullet_list,
  numbered_list,
  table,
  blockquote,
  placeholder
} = require('./md_parser');

function assertEqual(actual, expected, testName) {
  const actualStr = JSON.stringify(actual);
  const expectedStr = JSON.stringify(expected);
  if (actualStr !== expectedStr) {
    console.error(`FAIL: ${testName}`);
    console.error(`  Expected: ${expectedStr}`);
    console.error(`  Actual:   ${actualStr}`);
    return false;
  }
  console.log(`PASS: ${testName}`);
  return true;
}

function assertContains(actual, expected, testName) {
  const actualStr = JSON.stringify(actual);
  const expectedStr = JSON.stringify(expected);
  if (!actualStr.includes(expectedStr)) {
    console.error(`FAIL: ${testName}`);
    console.error(`  Expected to contain: ${expectedStr}`);
    console.error(`  Actual:   ${actualStr}`);
    return false;
  }
  console.log(`PASS: ${testName}`);
  return true;
}

let passed = 0;
let failed = 0;

// Test 1: Empty input
if (assertEqual(parseMarkdown(''), [], 'Empty input returns empty array')) passed++;
else failed++;

if (assertEqual(parseMarkdown(null), [], 'Null input returns empty array')) passed++;
else failed++;

if (assertEqual(parseMarkdown(undefined), [], 'Undefined input returns empty array')) passed++;
else failed++;

// Test 2: Basic heading and paragraph
const result1 = parseMarkdown('# Title\n\nParagraph');
const expected1 = [
  heading(1, 'Title'),
  paragraph('Paragraph')
];
if (assertEqual(result1, expected1, 'Heading and paragraph parsed correctly')) passed++;
else failed++;

// Test 3: Multiple heading levels
const result2 = parseMarkdown('# H1\n## H2\n### H3');
const expected2 = [
  heading(1, 'H1'),
  heading(2, 'H2'),
  heading(3, 'H3')
];
if (assertEqual(result2, expected2, 'Multiple heading levels parsed correctly')) passed++;
else failed++;

// Test 4: Fenced code block with language
const result3 = parseMarkdown('```javascript\nconst x = 1;\n```');
const expected3 = [
  code('javascript', 'const x = 1;')
];
if (assertEqual(result3, expected3, 'Fenced code block with language')) passed++;
else failed++;

// Test 5: Fenced code block without language
const result4 = parseMarkdown('```\nsome code\n```');
const expected4 = [
  code('', 'some code')
];
if (assertEqual(result4, expected4, 'Fenced code block without language')) passed++;
else failed++;

// Test 6: Bullet list
const result5 = parseMarkdown('- item 1\n- item 2\n- item 3');
const expected5 = [
  bullet_list(['item 1', 'item 2', 'item 3'])
];
if (assertEqual(result5, expected5, 'Bullet list parsed correctly')) passed++;
else failed++;

// Test 7: Numbered list
const result6 = parseMarkdown('1. first\n2. second\n3. third');
const expected6 = [
  numbered_list(['first', 'second', 'third'])
];
if (assertEqual(result6, expected6, 'Numbered list parsed correctly')) passed++;
else failed++;

// Test 8: Table
const result7 = parseMarkdown('| A | B |\n|---|---|\n| 1 | 2 |');
const expected7 = [
  table(['A', 'B'], [['1', '2']])
];
if (assertEqual(result7, expected7, 'Table parsed correctly')) passed++;
else failed++;

// Test 9: Blockquote
const result8 = parseMarkdown('> This is a quote');
const expected8 = [
  blockquote('This is a quote')
];
if (assertEqual(result8, expected8, 'Blockquote parsed correctly')) passed++;
else failed++;

// Test 10: Image placeholder
const result9 = parseMarkdown('[Image: diagram.png]');
const expected9 = [
  placeholder('Image: diagram.png')
];
if (assertEqual(result9, expected9, 'Image placeholder parsed correctly')) passed++;
else failed++;

// Test 11: External placeholder
const result10 = parseMarkdown('[External: https://example.com]');
const expected10 = [
  placeholder('External: https://example.com')
];
if (assertEqual(result10, expected10, 'External placeholder parsed correctly')) passed++;
else failed++;

// Test 12: Consecutive paragraphs
const result11 = parseMarkdown('First paragraph\n\nSecond paragraph');
const expected11 = [
  paragraph('First paragraph'),
  paragraph('Second paragraph')
];
if (assertEqual(result11, expected11, 'Consecutive paragraphs')) passed++;
else failed++;

// Test 13: Mixed content
const result12 = parseMarkdown('# Title\n\nSome text\n\n```js\ncode\n```\n\n- list');
const expected12 = [
  heading(1, 'Title'),
  paragraph('Some text'),
  code('js', 'code'),
  bullet_list(['list'])
];
if (assertEqual(result12, expected12, 'Mixed content')) passed++;
else failed++;

// Test 14: Bold inline (preserved as text)
const result13 = parseMarkdown('This has **bold** text');
if (assertContains(result13, 'This has **bold** text', 'Inline bold preserved')) passed++;
else failed++;

// Test 15: Inline code (preserved as text)
const result14 = parseMarkdown('This has `inline code` text');
if (assertContains(result14, 'This has `inline code` text', 'Inline code preserved')) passed++;
else failed++;

// Test 16: Bullet list with * syntax
const result15 = parseMarkdown('* item 1\n* item 2');
const expected15 = [
  bullet_list(['item 1', 'item 2'])
];
if (assertEqual(result15, expected15, 'Bullet list with * syntax')) passed++;
else failed++;

// Test 17: Table with multiple rows
const result16 = parseMarkdown('| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |');
const expected16 = [
  table(['A', 'B'], [['1', '2'], ['3', '4']])
];
if (assertEqual(result16, expected16, 'Table with multiple rows')) passed++;
else failed++;

// Summary
console.log(`\n--- Results: ${passed} passed, ${failed} failed ---`);
if (failed > 0) {
  process.exit(1);
}
