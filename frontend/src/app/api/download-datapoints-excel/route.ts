import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

export async function GET() {
  const filePath = path.join(
    process.cwd(),
    "..",
    "BRSR_DataPoints_Complete.xlsx"
  );

  try {
    const buffer = await readFile(filePath);
    return new NextResponse(buffer, {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition":
          'attachment; filename="BRSR_DataPoints_Complete.xlsx"',
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Excel file not found" },
      { status: 404 }
    );
  }
}
