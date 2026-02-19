/**
 * Markdown parser that converts markdown text into typed block objects.
 */

/**
 * Creates a heading block.
 * @param {number} level - Heading level (1-3)
 * @param {string} text - Heading text
 * @returns {Object} Heading block
 */
function heading(level, text) {
  return { type: 'heading', level, text };
}

/**
 * Creates a paragraph block.
 * @param {string} text - Paragraph text
 * @returns {Object} Paragraph block
 */
function paragraph(text) {
  return { type: 'paragraph', text };
}

/**
 * Creates a code block.
 * @param {string} lang - Programming language
 * @param {string} content - Code content
 * @returns {Object} Code block
 */
function code(lang, content) {
  return { type: 'code', lang, content };
}

/**
 * Creates a bullet list block.
 * @param {string[]} items - List items
 * @returns {Object} Bullet list block
 */
function bullet_list(items) {
  return { type: 'bullet_list', items };
}

/**
 * Creates a numbered list block.
 * @param {string[]} items - List items
 * @returns {Object} Numbered list block
 */
function numbered_list(items) {
  return { type: 'numbered_list', items };
}

/**
 * Creates a table block.
 * @param {string[]} headers - Table headers
 * @param {string[][]} rows - Table rows
 * @returns {Object} Table block
 */
function table(headers, rows) {
  return { type: 'table', headers, rows };
}

/**
 * Creates a blockquote block.
 * @param {string} text - Quoted text
 * @returns {Object} Blockquote block
 */
function blockquote(text) {
  return { type: 'blockquote', text };
}

/**
 * Creates a placeholder block.
 * @param {string} text - Placeholder text
 * @returns {Object} Placeholder block
 */
function placeholder(text) {
  return { type: 'placeholder', text };
}

/**
 * Parses inline markdown (bold and code) within text.
 * @param {string} text - Text to parse
 * @returns {Object} Text with inline formatting preserved
 */
function parseInline(text) {
  return text;
}

/**
 * Parses markdown text into an array of typed block objects.
 * @param {string} text - Markdown text to parse
 * @returns {Object[]} Array of block objects
 */
function parseMarkdown(text) {
  if (!text || typeof text !== 'string') {
    return [];
  }

  const blocks = [];
  const lines = text.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Skip empty lines but continue processing
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Headings: # H1, ## H2, ### H3
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = headingMatch[2].trim();
      blocks.push(heading(level, text));
      i++;
      continue;
    }

    // Fenced code blocks: ```lang
    const codeBlockMatch = line.match(/^```(\w*)$/);
    if (codeBlockMatch) {
      const lang = codeBlockMatch[1] || '';
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      blocks.push(code(lang, codeLines.join('\n')));
      i++; // Skip closing ```
      continue;
    }

    // Blockquotes: > text
    if (line.startsWith('>')) {
      const text = line.slice(1).trim();
      blocks.push(blockquote(text));
      i++;
      continue;
    }

    // Tables: | header | header |
    const tableMatch = line.match(/^\|.+\|$/);
    if (tableMatch && i + 1 < lines.length && lines[i + 1].match(/^\|[\s-:\|]+$/)) {
      const headerLine = line;
      const separatorLine = lines[i + 1];

      // Parse headers
      const headers = headerLine
        .split('|')
        .filter(cell => cell.trim() !== '')
        .map(cell => cell.trim());

      // Skip separator line and parse rows
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].match(/^\|.+\|$/)) {
        const row = lines[i]
          .split('|')
          .filter(cell => cell.trim() !== '')
          .map(cell => cell.trim());
        rows.push(row);
        i++;
      }

      if (headers.length > 0) {
        blocks.push(table(headers, rows));
      }
      continue;
    }

    // Bullet lists: - item or * item
    if (line.match(/^[-*]\s+/)) {
      const items = [];
      while (i < lines.length && lines[i].match(/^[-*]\s+/)) {
        const item = lines[i].replace(/^[-*]\s+/, '');
        items.push(item);
        i++;
      }
      if (items.length > 0) {
        blocks.push(bullet_list(items));
      }
      continue;
    }

    // Numbered lists: 1. item
    if (line.match(/^\d+\.\s+/)) {
      const items = [];
      while (i < lines.length && lines[i].match(/^\d+\.\s+/)) {
        const item = lines[i].replace(/^\d+\.\s+/, '');
        items.push(item);
        i++;
      }
      if (items.length > 0) {
        blocks.push(numbered_list(items));
      }
      continue;
    }

    // Placeholders: [Image: x] or [External: x]
    const placeholderMatch = line.match(/^\[(Image|External):\s*(.+)\]$/);
    if (placeholderMatch) {
      const placeholderText = `${placeholderMatch[1]}: ${placeholderMatch[2]}`;
      blocks.push(placeholder(placeholderText));
      i++;
      continue;
    }

    // Regular paragraph
    blocks.push(paragraph(line));
    i++;
  }

  return blocks;
}

module.exports = {
  parseMarkdown,
  heading,
  paragraph,
  code,
  bullet_list,
  numbered_list,
  table,
  blockquote,
  placeholder,
  parseInline
};
