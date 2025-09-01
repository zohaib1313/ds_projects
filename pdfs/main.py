import os
import shutil

# -------- CONFIG --------
main_folder = "/Users/muhammadzohaib/Desktop/ds_projects/pdfs/INVOICE"   # source folder containing PDFs
dest_folder = "/Users/muhammadzohaib/Desktop/ds_projects/pdfs/destination"  # destination base folder
group_size = 4  # how many PDFs per folder
# ------------------------

def copy_pdfs():
    # Ensure destination exists
    os.makedirs(dest_folder, exist_ok=True)

    # Get all pdfs from main folder
    all_files = [f for f in os.listdir(main_folder) if f.lower().endswith(".pdf")]
    print(f"Found {len(all_files)} PDF files.")
    
    folder_index = 1

    for i in range(0, len(all_files), group_size):
        group = all_files[i:i + group_size]
        current_folder = os.path.join(dest_folder, f"folder_{folder_index}")

        # Create subfolder if not exists
        os.makedirs(current_folder, exist_ok=True)

        # Copy files
        for file in group:
            src = os.path.join(main_folder, file)
            dest = os.path.join(current_folder, file)
            shutil.copy2(src, dest)  # keeps metadata
            print(f"Copied {file} → {current_folder}")

        folder_index += 1

    print("✅ PDFs copied successfully.")

if __name__ == "__main__":
    copy_pdfs()
