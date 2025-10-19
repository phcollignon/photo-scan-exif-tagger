import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
from tkintermapview import TkinterMapView
import os
import shutil
import piexif
from PIL import Image
import datetime

# Set application appearance (Dark mode, Blue theme)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PhotoImporterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Photo Scan Exif Tagger v1.0")
        self.geometry("1100x850")

        # Variables to store states
        self.source_dir = ctk.StringVar()
        self.target_dir = ctk.StringVar()
        self.selected_album = ctk.StringVar()
        self.selected_gps = None  # Will store (latitude, longitude)
        self.map_marker = None

        # Configure the main grid
        # Column 1 (map) will be wider
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=0)  # Row for directories
        self.grid_rowconfigure(1, weight=0)  # Row for album
        self.grid_rowconfigure(2, weight=1)  # Row for calendar + map
        self.grid_rowconfigure(3, weight=0)  # Row for import button

        self.create_directory_widgets()
        self.create_album_widgets()
        self.create_date_widgets()
        self.create_map_widgets()
        self.create_action_widgets()

    ## 1. Directory Widgets
    def create_directory_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        # Source
        ctk.CTkLabel(frame, text="Source Directory:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        ctk.CTkEntry(frame, textvariable=self.source_dir).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame, text="Browse...", command=self.select_source).grid(row=0, column=2, padx=(5, 10), pady=5)

        # Target
        ctk.CTkLabel(frame, text="Albums Directory:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        ctk.CTkEntry(frame, textvariable=self.target_dir).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(frame, text="Browse...", command=self.select_target).grid(row=1, column=2, padx=(5, 10), pady=5)

    ## 2. Album Widgets
    def create_album_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Album:").grid(row=0, column=0, padx=(10, 5), pady=10)
        
        self.album_dropdown = ctk.CTkOptionMenu(frame, variable=self.selected_album, values=[""], state="disabled")
        self.album_dropdown.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        ctk.CTkButton(frame, text="Refresh ↻", command=self.refresh_albums).grid(row=0, column=2, padx=(5, 10), pady=10)

    ## 3. Date Widget
    def create_date_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame, text="Select a Date:").pack(pady=(10, 5))
        
        today = datetime.date.today()
        current_year = today.year
        
        ctk.CTkLabel(frame, text="Quick Year Select:").pack(pady=(10, 2))
        
        year_list = [str(y) for y in range(current_year, 1899, -1)]
        self.selected_year_var = ctk.StringVar(value=str(current_year))
        
        self.year_dropdown = ctk.CTkOptionMenu(frame,
                                               variable=self.selected_year_var,
                                               values=year_list,
                                               command=self.on_year_selected)
    
        self.year_dropdown.pack(padx=10, pady=(0, 10))

        # Default (small) calendar with year selection
        self.calendar = Calendar(frame, selectmode='day',
                                 year=today.year, month=today.month, day=today.day,
                                 date_pattern='y-mm-dd')
        
        self.calendar.pack(padx=10, pady=10, anchor="n")


    def on_year_selected(self, selected_year_str):
        """
        Callback for when a year is chosen from the dropdown.
        Sets the calendar to Jan 1st of that year.
        """
        try:
            year = int(selected_year_str)
            new_date = datetime.date(year, 1, 1)

            self.calendar.selection_set(new_date)
            
            # --- DEBUG MESSAGE ---
            print(f"[Debug] Quick Year selected: {selected_year_str}. Calendar set to {new_date}.")
            # ---------------------
            
        except Exception as e:
            print(f"Error setting year: {e}")
            messagebox.showerror("Error", "Invalid year selected.")

    ## 4. Map Widgets
    def create_map_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        
        frame.grid_rowconfigure(1, weight=1) # Row 1 for map
        frame.grid_rowconfigure(0, weight=0) # Row 0 for search
        frame.grid_rowconfigure(2, weight=0) # Row 2 for status/button
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)

        self.search_entry = ctk.CTkEntry(frame, placeholder_text="Search by city name...")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=(10, 5))
        self.search_entry.bind("<Return>", lambda event: self.search_location())
        
        self.search_button = ctk.CTkButton(frame, text="Search", width=80, command=self.search_location)
        self.search_button.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=(10, 5))

        self.map_widget = TkinterMapView(frame, corner_radius=10)
        self.map_widget.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10)

        
        self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        self.map_widget.set_position(48.8566, 2.3522) # Paris
        self.map_widget.set_zoom(10)

        self.map_widget.add_right_click_menu_command(label="Set Location",
                                                     command=self.set_gps_marker,
                                                     pass_coords=True)

        self.gps_label = ctk.CTkLabel(frame, text="GPS Location: Not set")
        self.gps_label.grid(row=2, column=0, pady=(5, 10), sticky="w", padx=10)

        ctk.CTkButton(frame, text="Clear Location", command=self.clear_gps).grid(row=2, column=1, pady=(5, 10), sticky="e", padx=10)

    ## 5. Action (Import) Widget
    def create_action_widgets(self):
        self.import_button = ctk.CTkButton(self, text="Tag & Copy Photos", height=50, command=self.run_import, font=("Arial", 16))
        self.import_button.grid(row=3, column=0, columnspan=2, padx=10, pady=15, sticky="ew")

    def select_source(self):
        path = filedialog.askdirectory(title="Select Source Directory")
        if path:
            self.source_dir.set(path)

    def select_target(self):
        path = filedialog.askdirectory(title="Select Target Directory (parent of albums)")
        if path:
            self.target_dir.set(path)

            try:
                subdirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                if not subdirs:
                    messagebox.showwarning("Empty Directory", 
                                         "This folder is empty.\n\nThe 'Albums Directory' should be a parent folder that already contains subfolders (albums).")
            except Exception as e:
                messagebox.showerror("Error", f"Could not read directory: {e}")
            
            self.refresh_albums() # This will still run to update the list
    def refresh_albums(self):
        target = self.target_dir.get()
        if not os.path.isdir(target):
            messagebox.showwarning("Missing Directory", "Please select a valid Target directory first.")
            return

        try:
            subdirs = [d for d in os.listdir(target) if os.path.isdir(os.path.join(target, d))]
            if not subdirs:
                subdirs = ["(No albums found)"]
                self.album_dropdown.configure(state="disabled")
                self.selected_album.set("")
            else:
                self.album_dropdown.configure(values=subdirs, state="normal")
                self.selected_album.set(subdirs[0])
        except Exception as e:
            messagebox.showerror("Read Error", f"Could not read albums: {e}")

    def search_location(self):
        query = self.search_entry.get()
        if not query:
            return

        self.map_widget.set_address(query)
        coords = self.map_widget.get_position()
        
        self.set_gps_marker(coords)
        
        self.map_widget.set_zoom(13)

    def set_gps_marker(self, coords):
        # --- DEBUG MESSAGE ---
        print(f"[Debug] GPS Location Set: {coords}")
        # ---------------------
        
        self.selected_gps = coords  # (lat, lon)
        self.gps_label.configure(text=f"GPS Location: {coords[0]:.6f}, {coords[1]:.6f}")

        if self.map_marker:
            self.map_marker.delete()

        self.map_marker = self.map_widget.set_marker(coords[0], coords[1], text="Import")

    def clear_gps(self):
        # --- DEBUG MESSAGE ---
        print("[Debug] GPS Location Cleared.")
        # ---------------------
        
        self.selected_gps = None
        self.gps_label.configure(text="GPS Location: Not set")
        if self.map_marker:
            self.map_marker.delete()
            self.map_marker = None

    def run_import(self):
        # 1. Validation
        source = self.source_dir.get()
        target = self.target_dir.get()
        album = self.selected_album.get()

        if not all([source, target, album]) or album == "(No albums found)":
            messagebox.showerror("Incomplete Fields", "Please select a source directory, target directory, and a valid album.")
            return
        destination_path = os.path.join(target, album)
        if not os.path.isdir(destination_path):
            messagebox.showerror("Error", f"The album path '{destination_path}' does not exist or is not a directory.")
            return
        
        # 2. Get data
        try:
            selected_date = self.calendar.get_date()
            date_obj = datetime.datetime.strptime(selected_date, '%Y-%m-%d')
            exif_date_str = date_obj.strftime("%Y:%m:%d %H:%M:%S")
            exif_date_bytes = exif_date_str.encode('utf-8')
        except Exception as e:
            messagebox.showerror("Invalid Date", f"Invalid date selected: {e}")
            return
        
        gps_data = self.selected_gps
        
        # --- DEBUG MESSAGES ---
        print("="*30)
        print(f"[Debug] Import started with Date: {selected_date}")
        print(f"[Debug] Import started with GPS: {gps_data if gps_data else 'None'}")
        print("="*30)
        # ----------------------
        
        # 3. Start process
        self.process_files(source, destination_path, exif_date_bytes, gps_data)

    def process_files(self, source_dir, dest_dir, exif_date, gps_data):

        image_files = [f for f in os.listdir(source_dir) 
                       if f.lower().endswith(('.jpg', '.jpeg'))]

        if not image_files:
            messagebox.showinfo("Info", "No .jpg or .jpeg files found in the source directory.")
            return
        
        total = len(image_files)
        processed_count = 0
        error_count = 0
        error_list = [] 

        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Import in progress...")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()

        ctk.CTkLabel(progress_window, text="Processing photos...").pack(pady=10)
        progress_label = ctk.CTkLabel(progress_window, text=f"Photo 0 / {total}")
        progress_label.pack(pady=5)
        progress_bar = ctk.CTkProgressBar(progress_window, width=360)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        exif_gps_dict = {}
        if gps_data:
            exif_gps_dict = self.convert_gps_to_exif(gps_data[0], gps_data[1])

        for i, filename in enumerate(image_files):
            try:
                progress_label.configure(text=f"Photo {i+1} / {total}: {filename}")
                progress_bar.set((i + 1) / total)
                self.update_idletasks() 

                source_file = os.path.join(source_dir, filename)
                dest_file = os.path.join(dest_dir, filename)

                # --- DEBUG MESSAGE ---
                print(f"\n[Debug] Processing: {filename}\n  From: {source_file}\n  To:   {dest_file}")
                # ---------------------

                img = Image.open(source_file)
                
                # Load EXIF
                try:
                    exif_dict = piexif.load(img.info.get('exif', b''))
                except piexif.InvalidImageDataError:
                    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
                
                if "0th" not in exif_dict: exif_dict["0th"] = {}
                if "Exif" not in exif_dict: exif_dict["Exif"] = {}
                if "GPS" not in exif_dict: exif_dict["GPS"] = {}

                # 1. OVERWRITE "Date Taken" fields only.
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = exif_date
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = exif_date

                # 2. Add/Overwrite GPS
                if gps_data:
                    exif_dict["GPS"] = exif_gps_dict
                
                # Fix piexif bugs (int vs bytes)
                if piexif.ExifIFD.SceneType in exif_dict["Exif"]:
                    val = exif_dict["Exif"][piexif.ExifIFD.SceneType]
                    if isinstance(val, int):
                        exif_dict["Exif"][piexif.ExifIFD.SceneType] = val.to_bytes(1, 'big')

                if piexif.ExifIFD.FileSource in exif_dict["Exif"]:
                    val = exif_dict["Exif"][piexif.ExifIFD.FileSource]
                    if isinstance(val, int):
                        exif_dict["Exif"][piexif.ExifIFD.FileSource] = val.to_bytes(1, 'big')
                
                # Save
                exif_bytes = piexif.dump(exif_dict)
                img.save(dest_file, exif=exif_bytes)
                img.close()
                
                processed_count += 1

            except Exception as e:
                print(f"Error while processing {filename}: {e}")
                error_count += 1
                error_list.append(filename)
        
        # --- DEBUG MESSAGE ---
        print(f"\n[Debug] Processing complete. {processed_count} files tagged, {error_count} errors.")
        print("="*30)
        # ---------------------

        # End
        progress_window.destroy()
        
        msg = f"Import complete!\n\nPhotos processed: {processed_count}\nErrors: {error_count}"
        if error_count > 0:
            msg += f"\n\nFiles with errors (see console for details):\n" + "\n".join(error_list[:5])
            if error_count > 5:
                msg += "\n..."
        
        messagebox.showinfo("Import Complete", msg)

    def convert_gps_to_exif(self, latitude, longitude):
        """Converts decimal GPS coordinates to EXIF rational format."""
        
        def to_rational(decimal_coord):
            abs_coord = abs(decimal_coord)
            deg_num = int(abs_coord)
            min_num = int((abs_coord - deg_num) * 60)
            sec_num = int(((abs_coord - deg_num) * 60 - min_num) * 60 * 10000)
            sec_den = 10000
            
            return [
                (deg_num, 1),
                (min_num, 1),
                (sec_num, sec_den)
            ]

        lat_ref = b'N' if latitude >= 0 else b'S'
        lat_exif = to_rational(latitude)
        
        lon_ref = b'E' if longitude >= 0 else b'W'
        lon_exif = to_rational(longitude)

        return {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: lat_exif,
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLongitude: lon_exif,
        }

if __name__ == "__main__":
    app = PhotoImporterApp()
    app.mainloop()