#!/usr/bin/env node

import { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, BorderStyle, ImageRun, VerticalAlign } from "docx";
import { readFileSync, existsSync } from "fs";

/**
 * Convert JSON structure to DOCX
 * CLI: node converter.js <jsonPath> <docxPath>
 */

function error(message) {
  process.stderr.write(message + "\n");
  process.exit(1);
}

function loadJson(jsonPath) {
  try {
    const content = readFileSync(jsonPath, "utf-8");
    return JSON.parse(content);
  } catch (e) {
    error(`Failed to parse JSON: ${e.message}`);
  }
}

function createTextRun(text, formatting = []) {
  return new TextRun({
    text,
    bold: formatting.includes("bold"),
    italics: formatting.includes("italic"),
    underline: formatting.includes("underline") ? {} : undefined,
  });
}

function mapSection(section) {
  switch (section.type) {
    case "heading1":
      return new Paragraph({
        text: section.text,
        heading: HeadingLevel.HEADING_1,
      });

    case "heading2":
      return new Paragraph({
        text: section.text,
        heading: HeadingLevel.HEADING_2,
      });

    case "heading3":
      return new Paragraph({
        text: section.text,
        heading: HeadingLevel.HEADING_3,
      });

    case "paragraph": {
      const runs = section.text.split("").map((char) =>
        createTextRun(char, section.formatting || [])
      );
      return new Paragraph({
        children: runs.length > 0 ? runs : [new TextRun({ text: "" })],
      });
    }

    case "code_block": {
      const code = section.code || "";
      const lines = code.split("\n");
      return lines.map((line) =>
        new Paragraph({
          text: line,
          style: "Code",
        })
      );
    }

    case "table": {
      const headers = section.headers || [];
      const rows = section.rows || [];

      const headerCells = headers.map((h) =>
        new TableCell({
          children: [
            new Paragraph({
              children: [new TextRun({ text: h, bold: true })],
            }),
          ],
          verticalAlign: VerticalAlign.CENTER,
        })
      );

      const headerRow = new TableRow({
        children: headerCells,
        tableHeader: true,
      });

      const dataRows = rows.map((row) =>
        new TableRow({
          children: row.map((cell) =>
            new TableCell({
              children: [new Paragraph({ text: cell || "" })],
              verticalAlign: VerticalAlign.CENTER,
            })
          ),
        })
      );

      return new Table({
        rows: [headerRow, ...dataRows],
        width: {
          size: 100,
          type: WidthType.PERCENTAGE,
        },
      });
    }

    case "image": {
      const imagePath = section.path;
      if (!existsSync(imagePath)) {
        error(`Image file not found: ${imagePath}`);
      }

      const imageBuffer = readFileSync(imagePath);
      const width = section.width || 200;
      const height = section.height || 200;

      return new Paragraph({
        children: [
          new ImageRun({
            data: imageBuffer,
            transformation: {
              width,
              height,
            },
          }),
        ],
      });
    }

    default:
      return new Paragraph({ text: "" });
  }
}

async function convert(jsonPath, docxPath) {
  const data = loadJson(jsonPath);

  const sections = data.sections || [];

  const docChildren = [];

  for (const section of sections) {
    const elements = mapSection(section);
    if (Array.isArray(elements)) {
      docChildren.push(...elements);
    } else {
      docChildren.push(elements);
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: docChildren,
      },
    ],
    styles: {
      paragraphStyles: [
        {
          id: "Code",
          name: "Code",
          run: {
            font: "Courier New",
          },
        },
      ],
    },
  });

  const buffer = await Packer.toBuffer(doc);

  const { writeFileSync } = await import("fs");
  writeFileSync(docxPath, buffer);

  console.log(`Created DOCX: ${docxPath}`);
}

// Main entry point
const [, , jsonPath, docxPath] = process.argv;

if (!jsonPath || !docxPath) {
  error("Usage: node converter.js <jsonPath> <docxPath>");
}

await convert(jsonPath, docxPath);
