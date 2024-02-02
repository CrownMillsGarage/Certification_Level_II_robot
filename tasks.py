from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Tables import Tables
from RPA.Images import Images
from PIL import Image
from bs4 import BeautifulSoup
from io import BytesIO
from RPA.PDF import PDF
from RPA.Archive import Archive
import datetime
import os

@task
def order_robots_from_RobotSpareBin():
    """
    Orders robots from RobotSpareBin Industries Inc.
    Saves the order HTML receipt as a PDF file.
    Saves the screenshot of the ordered robot.
    Embeds the screenshot of the robot to the PDF receipt.
    Creates ZIP archive of the receipts and the images.
    """
    #browser.configure(
    #    slowmo=200,
    #)
    open_robot_order_website()
    #log_in()
    orders = get_orders()
    fill_the_form(orders)
    archive_receipts()
    remove_temp_file()


def open_robot_order_website():
    """Open website"""
    browser.goto("https://robotsparebinindustries.com/")

def log_in():
    """Fills in the login form and clicks the 'Log in' button"""
    page = browser.page()
    page.fill("#username", "maria")
    page.fill("#password", "thoushallnotpass")
    page.click("button:text('Log in')")

def get_orders():
    """Downloads csv file from the given URL"""
    http = HTTP()
    http.download(url="https://robotsparebinindustries.com/orders.csv", overwrite=True)
    library = Tables()
    orders = library.read_table_from_csv("orders.csv")
    return orders

def close_annoying_modal(page):
    """Close annoying modal"""
    page.click("button:text('Yep')")
    
def fill_the_form(orders):
    """Fill the order form"""
 
    browser.goto("https://robotsparebinindustries.com/#/robot-order")
    page = browser.page()
    placeholder_text = "Enter the part number for the legs"

    for row in orders:
        
        close_annoying_modal(page)
        #example
        #print(row)
        #{'Order number': '1', 'Head': '1', 'Body': '2', 'Legs': '3', 'Address': 'Address 123'}
        
        page.fill(f"//input[@placeholder='{placeholder_text}']", str(row['Legs']))
        page.select_option("#head", str(row['Head']))
        
        id_to_select = "id-body-" + str(row['Body'])
        page.click(f"//div[@class='radio form-check']//input[@id='{id_to_select}']")
        
        page.fill("#address", str(row["Address"]))
        page.click("#preview")
        
        #Should there be a some sort of robot preview? I don't get it.

        do_not_proceed = 1
        while do_not_proceed != 0:
            page.click("#order")
            do_not_proceed = is_there_an_error(page)
            #print(do_not_proceed)  
        
        #There could be an error for example:
        #<div class="alert alert-danger" role="alert">Have You Tried Turning It On And Off Again?</div>
        #if error - just try click order again  

        pdf_file = store_receipt_as_pdf(str(row['Order number']))
        screenshot = screenshot_robot(str(row['Order number']))
        embed_screenshot_to_receipt(screenshot, pdf_file)

        #only one for testing purposes
        #break 
        page.click("#order-another")

def remove_temp_file():   
    """Remove temp screenshot-file"""
    if os.path.exists("combined_image.png"):
        os.remove("combined_image.png")

def is_there_an_error(page):
    """Check page for errors"""
    html_body = page.content()

    soup = BeautifulSoup(html_body, 'html.parser')
        
    # Find all div elements with class "alert alert-danger"
    error_divs = soup.find_all('div', class_='alert alert-danger')

    # Check if any matching divs were found
    if error_divs:
        return 1
    else: 
        return 0

def store_receipt_as_pdf(order_number):
    """Export the data to a pdf file"""
    page = browser.page()
    receipt_html = page.locator("#receipt").inner_html()

    pdf = PDF()
    filename = "output/receipts/receipt_order_"+ order_number +".pdf"
    pdf.html_to_pdf(receipt_html, filename)

    return filename

def screenshot_robot(order_number):
    """Take a screenshot of the robots picture"""
    page = browser.page()
    
    images = [] 
    images.append(Image.open(BytesIO(page.get_by_alt_text("Head").screenshot())))
    images.append(Image.open(BytesIO(page.get_by_alt_text("Body").screenshot())))
    images.append(Image.open(BytesIO(page.get_by_alt_text("Legs").screenshot())))
    
    # Combine images
    combined_image = combine_multiple_images(images)
    
    #image_html = page.locator("#robot-preview-image").inner_html()
    #return image_html
    
    return combined_image
    # Save or display the combined image
    #combined_image.show()  # Display the combined image
    #combined_image.save('combined_image.png')  # Save the combined image

def combine_multiple_images(images):
    """Combine multiple pictures"""
    # Get dimensions for the final image
    
    widths, heights = zip(*(img.size for img in images))
    max_width = max(widths)
    total_height = sum(heights)

    # Create a blank image with the total dimensions
    combined_image = Image.new('RGB', (max_width, total_height))
    
    # Paste each image into the combined image
    y_offset = 0
    for img in images:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.size[1]

    #should I need to resize the image? Nope.
    #width = combined_image.width * 0.5
    #height = combined_image.height * 0.5
    #print("Old width:",combined_image.width,"and height:",combined_image.height)
    #print("New width:",int(width),"and height:",int(height))
    #resized_image = combined_image.resize((int(width), int(height)), Image.Resampling.NEAREST)

    return combined_image

def embed_screenshot_to_receipt(screenshot, pdf_file):
    """Embed robot picture to the pdf-file"""
    
    # Save the combined image
    screenshot.save('combined_image.png')  
    
    #f = Image.open(BytesIO(screenshot))
    #with tempfile.NamedTemporaryFile(suffix=".png") as tf:
    #    f.save(tf, format="png")

    #TypeError: expected str, bytes or os.PathLike object, not BytesIO
    #buf = BytesIO()
    #screenshot.save(buf, 'png')
    #buf.seek(0)

    #a bytes-like object is required, not 'Image'
    #f = BytesIO(screenshot)

    #expected str, bytes or os.PathLike object, not Image
    #f = screenshot

    #just to be sure
    #print("Screenshot size:",screenshot.size)
    
    pdf = PDF()
    list_of_files = ['combined_image.png:align=center']
    
    pdf.add_files_to_pdf(files=list_of_files, target_document=pdf_file, append=True)

def archive_receipts():
    """Archiving receipts to a single zip-file"""

    lib = Archive()
    timestamp = str(datetime.datetime.now().strftime("%Y-%m-%d %H%M%S"))
    filename = "receipts-"+ timestamp +".zip"

    try:
        lib.archive_folder_with_zip('./output/receipts', filename, recursive=True)
        files = lib.list_archive(filename)
        #for file in files:
        #    print(file)
    except:
        print("Something went wrong when trying to archive.")