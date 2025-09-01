const fs = require("fs");
const path = require("path");

// -------- CONFIG --------
const mainFolder = "/Users/muhammadzohaib/Desktop/ds_projects/pdfs/INVOICE";   // source folder containing PDFs
const destFolder = "/Users/muhammadzohaib/Desktop/ds_projects/pdfs/destination"; // destination base folder
const groupSize = 4; // how many PDFs per folder
// ------------------------

function copyPDFs() {
  // Ensure destination exists
  if (!fs.existsSync(destFolder)) {
    fs.mkdirSync(destFolder, { recursive: true });
  }

  // Get all pdfs from main folder
  const allFiles = fs.readdirSync(mainFolder).filter(file => file.endsWith(".pdf"));

  let folderIndex = 1;

  for (let i = 0; i < allFiles.length; i += groupSize) {
    const group = allFiles.slice(i, i + groupSize);
    const currentFolder = path.join(destFolder, `folder_${folderIndex}`);

    // Create subfolder if not exists
    if (!fs.existsSync(currentFolder)) {
      fs.mkdirSync(currentFolder, { recursive: true });
    }

    // Copy files
    group.forEach(file => {
      const src = path.join(mainFolder, file);
      const dest = path.join(currentFolder, file);
      fs.copyFileSync(src, dest);
      console.log(`Copied ${file} → ${currentFolder}`);
    });

    folderIndex++;
  }

  console.log("✅ PDFs copied successfully.");
}

copyPDFs();
