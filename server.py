import streamlit as st
import folium
from streamlit_folium import st_folium
import re
import lotplotter
import io
import datetime
import csv
import ezdxf
import simplekml
import shapefile
import os
import zipfile
import json

####################################################################
# CONFIG
####################################################################
st.set_page_config(
   page_title="Improved Lot Boundary Plotter",
   page_icon="images/logo_icon.png",
   layout="wide",
   initial_sidebar_state="expanded",
)

st.logo("images/logo.png", size="large", icon_image="images/logo_icon.png")


####################################################################
# INITIALIZATION
####################################################################
if "td_data" not in st.session_state:
    st.session_state["td_data"] = []

st.session_state["notif_td_data"] = []

if "page_index" not in st.session_state:
    st.session_state["page_index"] = 0

if "process_paste_confirmed" not in st.session_state:
    st.session_state["process_paste_confirmed"] = False

if "process_csv_confirmed" not in st.session_state:
    st.session_state["process_csv_confirmed"] = False

if "points" not in st.session_state:
    st.session_state["points"] = []

if "geographic" not in st.session_state:
    st.session_state["geographic"] = []

if "tiepoint_data" not in st.session_state:
    with open("tiepoints.json", "r") as file:
        st.session_state["tiepoint_data"] = json.load(file)

####################################################################
# FUNCTIONS
####################################################################
@st.dialog("⚠️Confirmation Required")
def process_csv(data):
    st.warning("This action will overwrite your existing Technical Description Data.")
    st.warning("Are you sure you want to proceed?")
    cols = st.columns(2)
    with cols[0]:
        if st.button("Confirm", use_container_width=True):
            st.session_state["td_data"] = data
            st.session_state["page_index"] = 0
            st.session_state["process_csv_confirmed"] = True
            st.rerun()
    with cols[1]:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

@st.dialog("⚠️Confirmation Required")
def process_paste_text(data):
    st.warning("This action will overwrite your existing Technical Description Data.")
    st.warning("Are you sure you want to proceed?")
    cols = st.columns(2)
    with cols[0]:
        if st.button("Confirm", use_container_width=True):
            st.session_state["td_data"] = data
            st.session_state["page_index"] = 0
            st.session_state["process_paste_confirmed"] = True
            st.rerun()
    with cols[1]:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def display_td_data(data):
    if data["ns"] == "DS":
        return f"Due South, {data['dist']:.2f}"
    elif data["ns"] == "DN":
        return f"Due North, {data['dist']:.2f}"
    elif data["ns"] == "DE":
        return f"Due East, {data['dist']:.2f}"
    elif data["ns"] == "DW":
        return f"Due West, {data['dist']:.2f}"
    else:
        return f"{data['ns']} {data['deg']:02}-{data['min']:02} {data['ew']}, {data['dist']:.2f}"

def display_line(index):
    return f"{'TP-1' if index == 0 else (f'{index}-{index+1}' if index < len(st.session_state['td_data']) - 1 else f'{index}-1')}:"

def validate_manual_input_form():
    data = {"ns": st.session_state["new_ns"].upper(), 
        "deg": st.session_state["new_deg"], 
        "min": st.session_state["new_min"], 
        "ew": st.session_state["new_ew"].upper(), 
        "dist": st.session_state["new_dist"]}
    valid = True
    if data["ns"] in ["DN","DS","DW","DE"]:
        data["deg"] = 0
        data["min"] = 0
        data["ew"] = ""
    else:
        if data["ns"] not in ["N","S"]:
            notif_manual_input.error("Invalid input for NS. Please input 'N' for North or 'S' for South.")
            valid = False
        if data["ew"] not in ["E","W"]:
            notif_manual_input.error("Invalid input for EW. Please input 'E' for East or 'W' for West.")
            valid = False
    if valid:
        st.session_state["td_data"].append(data)
        st.toast(f"###### Added :green[{display_td_data(data)}]", icon="🟢")


def validate_update_form(index):
    data = {"ns": st.session_state[f"update_ns_{index}"].upper(), 
        "deg": st.session_state[f"update_deg_{index}"], 
        "min": st.session_state[f"update_min_{index}"], 
        "ew": st.session_state[f"update_ew_{index}"].upper(), 
        "dist": st.session_state[f"update_dist_{index}"]}
    valid = True
    if data["ns"] in ["DN","DS","DW","DE"]:
        data["deg"] = 0
        data["min"] = 0
        data["ew"] = ""
    else:
        if data["ns"] not in ["N","S"]:
            st.session_state["notif_td_data"][index].error("Invalid input for NS. Please input 'N' for North or 'S' for South.")
            valid = False
        if data["ew"] not in ["E","W"]:
            st.session_state["notif_td_data"][index].error("Invalid input for EW. Please input 'E' for East or 'W' for West.")
            valid = False
    if valid:
        st.session_state["td_data"][index] = data
        st.toast(f"###### Updated :green[{display_td_data(data)}]", icon="🟢")

def validate_import_csv_form():
    if st.session_state["csv_file"]:
        csv_file = st.session_state["csv_file"].read()
        decoded_data = csv_file.decode('utf-8')
        lines = decoded_data.split('\n')

        data = []
        valid = True
        for index, line in enumerate(lines):
            if line:
                split_line = re.split(r'[\t,]', line)

                if len(split_line) == 5:
                    ns, deg, min, ew, dist = (value.strip() for value in split_line)

                    if ns in ["NS","ns"] or deg in ["Deg", "Degrees","deg"] or min in ["Min","Minutes","min"] or ew in ["EW","ew"] or dist in ["Dist","Distance","dist"]:
                        continue
                    if ns in ["DS", "DW", "DN", "DE"]:
                        deg = 0
                        min = 0
                        ew = ""
                        try:
                            dist = float(dist)
                        except ValueError:
                            notif_import_csv.error(f"Invalid Dist value: {dist} from line {index+1}: **{line}**")
                            valid = False
                            break
                    else:
                        if ns not in ["N", "S"]:
                            notif_import_csv.error(f"Invalid NS value: {ns} from line {index+1}: **{line}**")
                            valid = False
                            break

                        try:
                            deg = int(deg)
                        except ValueError:
                            notif_import_csv.error(f"Invalid Deg value: {deg} from line {index+1}: **{line}**")
                            valid = False
                            break

                        try:
                            min = int(min)
                        except ValueError:
                            notif_import_csv.error(f"Invalid Min value: {min} from line {index+1}: **{line}**")
                            valid = False
                            break

                        if ew not in ["E", "W"]:
                            notif_import_csv.error(f"Invalid EW value: {ew} from line {index+1}: **{line}**")
                            valid = False
                            break

                        try:
                            dist = float(dist)
                        except ValueError:
                            notif_import_csv.error(f"Invalid Dist value: {dist} from line {index+1}: **{line}**")
                            valid = False
                            break

                    data.append({
                        "ns": ns.upper(), 
                        "deg": deg, 
                        "min": min, 
                        "ew": ew.upper(), 
                        "dist": dist})

                else:
                    notif_import_csv.error(f"Invalid value from line {index+1}: **{line}**")
                    valid = False
                    break

        if valid:
            if len(data):
                if st.session_state["td_data"]:
                    process_csv(data)
                else:
                    st.session_state["td_data"] = data
                    st.session_state["page_index"] = 0
                    st.session_state["process_csv_confirmed"] = True
            else:
                notif_import_csv.error("No Data")

def validate_paste_text_form():
    paste_text = st.session_state["paste_text"]
    lines = paste_text.split('\n')
    data = []
    valid = True
    for index, line in enumerate(lines):
        if line:
            split_line = re.split(r'[\t,]', line)

            if len(split_line) == 5:
                ns, deg, min, ew, dist = (value.strip() for value in split_line)

                if ns in ["NS","ns"] or deg in ["Deg", "Degrees","deg"] or min in ["Min","Minutes","min"] or ew in ["EW","ew"] or dist in ["Dist","Distance","dist"]:
                    continue

                if ns in ["DS", "DW", "DN", "DE"]:
                    deg = 0
                    min = 0
                    ew = ""
                    try:
                        dist = float(dist)
                    except ValueError:
                        notif_import_csv.error(f"Invalid Dist value: {dist} from line {index+1}: **{line}**")
                        valid = False
                        break
                else:

                    if ns not in ["N", "S"]:
                        notif_paste.error(f"Invalid NS value: {ns} from line {index+1}: **{line}**")
                        valid = False
                        break

                    try:
                        deg = int(deg)
                    except ValueError:
                        notif_paste.error(f"Invalid Deg value: {deg} from line {index+1}: **{line}**")
                        valid = False
                        break

                    try:
                        min = int(min)
                    except ValueError:
                        notif_paste.error(f"Invalid Min value: {min} from line {index+1}: **{line}**")
                        valid = False
                        break

                    if ew not in ["E", "W"]:
                        notif_paste.error(f"Invalid EW value: {ew} from line {index+1}: **{line}**")
                        valid = False
                        break

                    try:
                        dist = float(dist)
                    except ValueError:
                        notif_paste.error(f"Invalid Dist value: {dist} from line {index+1}: **{line}**")
                        valid = False
                        break

                    data.append({
                        "ns": ns.upper(), 
                        "deg": deg, 
                        "min": min, 
                        "ew": ew.upper(), 
                        "dist": dist})

            else:
                notif_paste.error(f"Invalid value from line {index+1}: **{line}**")
                valid = False
                break

    if valid:
        if len(data):
            if st.session_state["td_data"]:
                process_paste_text(data)
            else:
                st.session_state["td_data"] = data
                st.session_state["page_index"] = 0
                st.session_state["process_paste_confirmed"] = True
        else:
            notif_paste.error("No Data")

# Define a function to validate the structure of the JSON data
def validate_json_format(data):
    # Expected keys for each tiepoint entry
    required_keys = ["name", "northing", "easting", "latitude", "longitude", "k_latitude", "k_longitude"]
    
    # Check if the data is a list
    if not isinstance(data, list):
        return False, "The JSON should be a list of tiepoint entries."

    # Check each tiepoint entry for the required keys and data types
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"Entry {idx + 1} is not a dictionary."
        
        # Check for required keys
        for key in required_keys:
            if key not in item:
                return False, f"Missing key '{key}' in entry {idx + 1}."
        
        # Check the data types of the fields
        if not isinstance(item["name"], str):
            return False, f"Invalid type for 'name' in entry {idx + 1}. Expected string."
        if not isinstance(item["northing"], (int, float)):
            return False, f"Invalid type for 'northing' in entry {idx + 1}. Expected number."
        if not isinstance(item["easting"], (int, float)):
            return False, f"Invalid type for 'easting' in entry {idx + 1}. Expected number."
        
        # Validate latitude and longitude subfields (assuming they should be dictionaries with degrees, minutes, and seconds)
        latitude = item.get("latitude", {})
        if not isinstance(latitude, dict) or not all(k in latitude for k in ["deg", "min", "sec"]):
            return False, f"Invalid format for 'latitude' in entry {idx + 1}."
        
        longitude = item.get("longitude", {})
        if not isinstance(longitude, dict) or not all(k in longitude for k in ["deg", "min", "sec"]):
            return False, f"Invalid format for 'longitude' in entry {idx + 1}."
        
        # Ensure k_latitude and k_longitude are numbers
        if not isinstance(item["k_latitude"], (int, float)):
            return False, f"Invalid type for 'k_latitude' in entry {idx + 1}. Expected number."
        if not isinstance(item["k_longitude"], (int, float)):
            return False, f"Invalid type for 'k_longitude' in entry {idx + 1}. Expected number."
    
    return True, "The JSON format is valid."

def validate_import_json():
            # Check if a file has been uploaded
        if st.session_state["json_file"] is not None:
            try:
                # Load the JSON data from the uploaded file
                data = json.load(st.session_state["json_file"])
                
                # Validate the format of the JSON data
                is_valid, message = validate_json_format(data)
                
                if is_valid:
                    st.session_state["tiepoint_data"] = data
                    st.success("JSON file imported and validated successfully.")
                else:
                    st.error(message)  # Show validation error message
            except json.JSONDecodeError:
                st.error("The file is not a valid JSON. Please upload a correct JSON file.")
            except Exception as e:
                st.error(f"An error occurred: {e}")



def delete(index):
    data = st.session_state['td_data'][index]
    del st.session_state['td_data'][index]
    st.toast(f"###### Deleted :green[{display_td_data(data)}]", icon="🟢")

def copy(index):
    data = st.session_state['td_data'][index]
    st.session_state['td_data'].insert(index, data)
    st.toast(f"###### Copied :green[{display_td_data(data)}]", icon="🟢")

def move_up(index):
    if index > 0:
        data = st.session_state['td_data'][index]
        st.session_state['td_data'][index], st.session_state['td_data'][index - 1] = (st.session_state['td_data'][index - 1], st.session_state['td_data'][index])
        st.toast(f"###### Moved up :green[{display_td_data(data)}]", icon="🟢")

def move_down(index):
    if index < len(st.session_state['td_data'])-1:
        data = st.session_state['td_data'][index]
        st.session_state['td_data'][index], st.session_state['td_data'][index + 1] = (st.session_state['td_data'][index + 1], st.session_state['td_data'][index])
        st.toast(f"###### Moved down :green[{display_td_data(data)}]", icon="🟢")

def tiepoint_names(data):
    return data["name"]

@st.cache_data
def map_folium(zoom):
    m = folium.Map(location=(10.3157, 123.8854),zoom_start=zoom, tiles=None, control_scale=True)

    folium.TileLayer(
        tiles='OpenStreetMap',
        attr='OpenStreetMap',
        name='Open Street Map',
        overlay=False,
        control=True,
        show=False,
        max_zoom=18
    ).add_to(m)

    folium.TileLayer(
        tiles='https://mt.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google Maps',
        name='Google Maps',
        overlay=False,
        control=True,
        show=False
    ).add_to(m)

    folium.TileLayer(
        tiles='https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Google Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

# Constants
ITEMS_PER_PAGE = 5

# Determine the total number of pages
total_pages = (len(st.session_state["td_data"]) - 1) // ITEMS_PER_PAGE + 1

# Function to go to the next page
def next_page():
    if st.session_state["page_index"] < total_pages - 1:
        st.session_state["page_index"] += 1

# Function to go to the previous page
def prev_page():
    if st.session_state["page_index"] > 0:
        st.session_state["page_index"] -= 1

def go_to_page():
    selected_page = st.session_state["goto_page"]
    st.session_state["page_index"] = selected_page - 1

# Slice the data to show only the items for the current page
start_idx = st.session_state["page_index"] * ITEMS_PER_PAGE
end_idx = start_idx + ITEMS_PER_PAGE
current_td_data = st.session_state["td_data"][start_idx:end_idx]

if st.session_state["process_paste_confirmed"]:
        st.session_state["process_paste_confirmed"] = False
        st.toast(f"###### Process Successful!", icon="🟢")
        st.balloons()

if st.session_state["process_csv_confirmed"]:
        st.session_state["process_csv_confirmed"] = False
        st.toast(f"###### Process Successful!", icon="🟢")
        st.snow()

# Function to generate CSV content as a string
def generate_csv():
    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=["ns", "deg", "min", "ew", "dist"])
        writer.writerow({"ns": "NS", "deg": "Deg", "min": "Min", "ew": "EW", "dist": "Dist"})
        writer.writerows(st.session_state["td_data"])
        return output.getvalue()

def generate_dxf():
    # Create a new DXF document with DXF version R2004
    doc = ezdxf.new(dxfversion='R2004')
    msp = doc.modelspace()

    # Create a polyline from the provided coordinates
    msp.add_lwpolyline(st.session_state["points"])

    with io.StringIO() as string_stream:
        # Write DXF to string stream
        doc.write(string_stream)
    
        # Convert string to bytes
        dxf_content = string_stream.getvalue().encode('utf-8')
    
    return dxf_content

def generate_kml():
    kml = simplekml.Kml()
    # Add a line connecting the points
    line = kml.newlinestring(name="Path", coords=st.session_state["geographic"])
    
    # If you need to return the KML as a string:
    return kml.kml()

def generate_shp():
    # Create a temporary directory for the shapefile
    temp_dir = 'temp_shapefile'
    os.makedirs(temp_dir, exist_ok=True)  # Create directory if it does not exist

    # Path for the shapefile
    shp_path = os.path.join(temp_dir, f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}")

    # Create a shapefile writer
    writer = shapefile.Writer(shp_path)
    writer.shapeType = shapefile.POLYLINE  # Set the shape type to polyline

    # Add fields and geometry
    writer.field('NAME', 'C', '40')  # Add a character field
    writer.line([st.session_state["geographic"]])  # Add the line geometry
    writer.record('Path')  # Add a record

    # Close the writer to finalize the shapefile
    writer.close()

    # Create a zip file containing the shapefile
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for ext in ['.shp', '.shx', '.dbf']:
            file_path = shp_path + ext
            zip_file.write(file_path, arcname=os.path.basename(file_path))

    # Move the cursor to the beginning of the BytesIO buffer
    zip_buffer.seek(0)
    try:
        temp_dir = 'temp_shapefile'
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            # os.rmdir(temp_dir)
    except Exception as e:
        print(f"Error deleting files in temp directory: {e}")

    # Return the zip buffer for download
    return zip_buffer



####################################################################
# SIDEBAR
####################################################################

with st.sidebar:
    tabs = st.tabs(["Manual Input", "Import", "Download", "Adjustment"])

    with tabs[0]:
        with st.form(key="manual_input_form"):
            notif_manual_input = st.container()

            cols = st.columns([1,1,1,1,1.5])
            new_ns = cols[0].text_input("NS", key="new_ns")
            new_deg = cols[1].number_input("Deg", min_value=0, max_value=90, key="new_deg")
            new_min = cols[2].number_input("Min", min_value=0, max_value=60, key="new_min")
            new_ew = cols[3].text_input("EW", key="new_ew")
            new_dist = cols[4].number_input("Dist", min_value=0.00, step=1.00, key="new_dist")

            add_line = st.form_submit_button("Add", on_click=validate_manual_input_form, icon=":material/add:")
        st.warning("Disclaimer: The output of this application is for viewing only and cannot be used for legal purposes. It is advised to seek assistance from a duly licensed Geodetic Engineer or verify from the mandated agencies (LMB and LRA).")

    with tabs[1]:
        with st.container(border=True):
            notif_import_csv = st.container()
            file_upload = st.file_uploader("Import CSV File", type=['csv'], key="csv_file", on_change=validate_import_csv_form)

        with st.form(key="Paste Text"):
            notif_paste = st.container()
            textarea = st.text_area("Paste Text", key="paste_text")
            process_text = st.form_submit_button("Process", icon=":material/memory:", on_click=validate_paste_text_form)

        with st.container(border=True):
            uploaded_file_json = st.file_uploader("Import Tiepoints JSON File", type="json", on_change=validate_import_json, key="json_file")


####################################################################
# MAIN
####################################################################

st.subheader("Improved Lot Boundary Plotter")

main_cols = st.columns([1,2])

with main_cols[0]:
    tiepoint = st.selectbox("Tiepoint", options=st.session_state["tiepoint_data"], index=None, format_func=tiepoint_names, key="tiepoint_selected")
    with st.container(border=True):
        st.write("Technical Descriptions")
        output_td_data = st.container()
        for index, data in enumerate(current_td_data):
            current_index = start_idx + index
            with output_td_data.popover(f"{display_line(current_index)} {display_td_data(data)}", use_container_width=True):
                with st.form(key=f"update_form_{current_index}"):
                    st.session_state["notif_td_data"].append(st.container())
                    update_cols = st.columns(5)
                    update_ns = update_cols[0].text_input("NS", value=data['ns'], key=f"update_ns_{current_index}")
                    update_deg = update_cols[1].number_input("Deg", min_value=0, max_value=90, value=data['deg'], key=f"update_deg_{current_index}")
                    update_min = update_cols[2].number_input("Min", min_value=0, max_value=60, value=data['min'], key=f"update_min_{current_index}")
                    update_ew = update_cols[3].text_input("EW", value=data['ew'], key=f"update_ew_{current_index}")
                    update_dist = update_cols[4].number_input("Dist", min_value=0.00, step=1.00, value=data['dist'], key=f"update_dist_{current_index}")
                    st.form_submit_button("Update", on_click=validate_update_form, args=(current_index,), icon=":material/update:")

                button_cols = st.columns(4)
                button_cols[0].button("Delete", key=f"delete_{current_index}", use_container_width=True, on_click=delete, args=(current_index,), icon=":material/delete:")
                button_cols[1].button("Copy", key=f"copy_{current_index}", use_container_width=True, on_click=copy, args=(current_index,), icon=":material/content_copy:")
                button_cols[2].button("Move Up", key=f"move_up_{current_index}", use_container_width=True, on_click=move_up, args=(current_index,), disabled=True if current_index==0 else False, icon=":material/arrow_upward:")
                button_cols[3].button("Move Down", key=f"move_down_{current_index}", use_container_width=True, on_click=move_down, args=(current_index,), disabled=False if current_index < len(st.session_state['td_data']) - 1 else True, icon=":material/arrow_downward:")

        # Pagination controls
        pagination_cols = st.columns(3)
        if st.session_state["td_data"]:
            with pagination_cols[0]:
                if st.session_state["page_index"] > 0:
                    st.button("Previous", on_click=prev_page, key="prev_page", use_container_width=True, disabled=False)
                else:
                    st.button("Previous", on_click=prev_page, key="prev_page", use_container_width=True, disabled=True)

            with pagination_cols[1]:
                st.html(f"<div style='text-align: center;'>Page {st.session_state['page_index'] + 1} of {total_pages}</div>")
                selected_page = st.number_input("Go to page:", min_value=1, max_value=total_pages, step=None, value=min(st.session_state["page_index"] + 1,total_pages), key="goto_page", on_change=go_to_page)

            with pagination_cols[2]:
                if st.session_state["page_index"] < total_pages - 1:
                    st.button("Next", on_click=next_page, key="next_page", use_container_width=True, disabled=False)
                else:
                    st.button("Next", on_click=next_page, key="next_page", use_container_width=True, disabled=True)

with tabs[3]:
    switch = st.toggle("Show tieline", key="switch")
    if tiepoint:
        with st.container(border=True):
            cols = st.columns(2)
            x_adjustment = cols[0].number_input("X Adjustment", step=1.00, format="%.3f", key="x_adjustment")
            y_adjustment = cols[1].number_input("Y Adjustment", step=1.00, format="%.3f", key="y_adjustment")  

with main_cols[1]:
    if st.session_state["tiepoint_selected"] and st.session_state["td_data"]:
        st.session_state["points"], st.session_state["geographic"], map_coord = lotplotter.calculate_boundary(st.session_state["tiepoint_selected"], st.session_state["td_data"])
        if st.session_state["switch"] == True:
            st.session_state["points"].insert(0,(st.session_state["tiepoint_selected"]["easting"],st.session_state["tiepoint_selected"]["northing"]))
            st.session_state["geographic"].insert(0,(lotplotter.convert_dms_to_dd(st.session_state["tiepoint_selected"]["longitude"]), lotplotter.convert_dms_to_dd(st.session_state["tiepoint_selected"]["latitude"])))
            map_coord.insert(0,(lotplotter.convert_dms_to_dd(st.session_state["tiepoint_selected"]["latitude"]), lotplotter.convert_dms_to_dd(st.session_state["tiepoint_selected"]["longitude"])))
        m = map_folium(18)
        adjusted_map_coord = [
            (lat + y_adjustment / (3600 * st.session_state["tiepoint_selected"]["k_latitude"]),
            long + x_adjustment / (3600 * st.session_state["tiepoint_selected"]["k_latitude"]))
            for lat, long in map_coord
        ]
        # Reverse
        st.session_state["geographic"] = [(coord[1], coord[0]) for coord in adjusted_map_coord]
        if st.session_state["switch"] == True:
            m.location = (adjusted_map_coord[1])
        else:
            m.location = (adjusted_map_coord[0])
        folium.PolyLine(locations=adjusted_map_coord,
            color="magenta",
            weight=5,
            fill_color="yellow",
            fill_opacity=0.6,
            fill=True,).add_to(m)
    else:
        m = map_folium(11)

    st_folium(m, height=500, use_container_width=True, returned_objects=[])

with tabs[2]:
    st.download_button(
        label="Download CSV",
        data=generate_csv(),
        file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv",
        mime="text/csv",
        use_container_width=True
    )

    if st.session_state["points"] and st.session_state["tiepoint_selected"]:
        st.download_button(
            label="Download DXF",
            data=generate_dxf(),
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.dxf",
            mime="application/dxf",
            use_container_width=True
        )
    else:
        st.download_button(
            label="Download DXF",
            data="",
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.dxf",
            mime="application/dxf",
            use_container_width=True,
            disabled=True
        )

    if st.session_state["geographic"] and st.session_state["tiepoint_selected"]:
        st.download_button(
            label="Download KML",
            data=generate_kml(),
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.kml",
            mime="application/kml",
            use_container_width=True
        )
    else:
        st.download_button(
            label="Download KML",
            data="",
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.kml",
            mime="application/kml",
            use_container_width=True,
            disabled=True
        )

    if st.session_state["geographic"] and st.session_state["tiepoint_selected"]:
        st.download_button(
            label="Download SHP",
            data=generate_shp(),
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip",
            mime="application/zip",
            use_container_width=True
        )
    else:
        st.download_button(
            label="Download SHP",
            data="",
            file_name=f"Lotplotter_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip",
            mime="application/zip",
            use_container_width=True,
            disabled=True
        )

    # Automatic download link in Streamlit
    st.download_button(
        label="Download Tiepoints JSON file",
        data=json.dumps(st.session_state["tiepoint_data"], indent=4),
        file_name="tiepoints_export.json",
        mime="application/json",
        use_container_width=True
    )