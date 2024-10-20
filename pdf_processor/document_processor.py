import fitz  # PyMuPDF
from .models import *

def extract_to_dict(pdf_path):
    # Open the PDF file
    doc = fitz.open(pdf_path)
    file_name = pdf_path.split('/')[-1]

    # Create a PDFDocument entry
    # pdf_document = PDFDocument.objects.create(file_name=file_name)
    pdf_content=[]

    # Iterate through each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_width, page_height = page.rect.width, page.rect.height

        rect = fitz.EMPTY_RECT()  # prepare an empty rectangle
        for item in page.get_bboxlog():
            b = item[1]  # the bbox of the covered area
            rect |= b[:4]  # join rect with the block bbox

        top_margin=rect.y0
        bottom_margin=page.rect.height - rect.y1

        pdf_content.append({
            "document" : pdf_path,
            "page_number" : page_num + 1,
            "width" : page_width,
            "height" : page_height,
            "top_margin" : top_margin,
            "bottom_margin" : bottom_margin,
            "content":[]
        })
        processed_bboxes=[]
        ignore_areas=[]
        tables = page.find_tables(strategy="lines_strict")
        if tables:
            for table in tables:
                ignore_areas.append(table.bbox)
                table_cells = table.cells
                table_content = table.extract()
                table_total_content=[]
                if table_cells and table_content:
                    table_cells = sorted(table_cells, key=lambda x: x[1])
                    cell_last_y=0
                    ret_data=[]
                    row_data=[]
                    for cell in table_cells:
                        if cell[1] != cell_last_y:
                            if row_data:
                                table_total_content.append(row_data)
                            row_data={
                                "bbox":cell,
                                "content":[]
                            }
                        cell_last_y=cell[1]
                        content = page.get_text("dict", cell)
                        # print("CELL CONTENT: ", content)
                        cell_content = {"bbox":cell,"content":[]}
                        for l in content["blocks"]:
                            print(l)
                            try:
                                line=l["lines"][0]
                            except:
                                print("failed to get line")
                                continue
                            ret_data = extract_data_from_line(line)
                            for i in ret_data:
                                processed_bboxes.append(i["bbox"])
                            # print("CELL LINE DATA: ", ret_data)
                            cell_content["content"].append(ret_data)
                        row_data["content"].append(cell_content)

                table_total_content.append(row_data)
                pdf_content[page_num]["content"].append(
                    {
                        "type": "table",
                        "bbox": table.bbox,
                        "page_num": page_num + 1,
                        "content": table_total_content
                    }
                )
        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            bbox = page.get_image_bbox(img_info)
            ignore_areas.append(tuple(bbox))

            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_path = f"static/extracted_image_page{page_num + 1}_img{img_index + 1}.{image_ext}"
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            pdf_content[page_num]["content"].append(
                {
                    "type": "image",
                    "bbox": tuple(bbox),
                    "page_num": page_num + 1,
                    "content": {
                        "file_path" : "/" + image_path,
                        "bbox":bbox,
                        "x" : bbox[0],
                        "y" : bbox[1],
                        "width" : bbox[2]-bbox[0],
                        "height" : bbox[3]-bbox[1],
                        "z_index" : img_index
                    }
                }
            )
        blocks = page.get_text("blocks")
        for block in blocks:
            block_content = []
            bbox = block[:4]
            contained = any(is_contained(bbox, ignore_bbox) for ignore_bbox in ignore_areas)
            if contained:
                continue
            content = page.get_text("dict", bbox)
            # print(content["blocks"])
            if content["blocks"]:
                try:
                    for line in content["blocks"][0]["lines"]:
                        ret_data = extract_data_from_line(line)
                        # print(ret_data)
                        if ret_data != []:
                            # print(ret_data)
                            block_content.append(ret_data)
                except:
                    print("failed to get line")
                    continue
            pdf_content[page_num]["content"].append(
                {"type": "text","bbox":bbox, "content": block_content}
            )
        sorted_lines = sorted(pdf_content[page_num]["content"], key=lambda x: (x["bbox"][1], x["bbox"][0]))
        pdf_content[page_num]["content"] = sorted_lines

    return pdf_content


def extract_data_from_line(line):
    ret_data=[]
    for span in line["spans"]:
        data = {}
        if span["text"] != "" and span["text"] != " ":
            bbox = span["bbox"]
            data["bbox"]=bbox
            data["text"]=span["text"]
            data["x"] = bbox[0]
            data["width"] = bbox[2] - bbox[0]
            data["y"] = bbox[1]
            data["font_size"] = span["size"]
            data["font_weight"] = "bold" if span["flags"] & 2 else "normal"
            data["font_color"] = f"#{span['color']:06x}"
            ret_data.append(data)
    return ret_data


# Define a function to check if bbox1 is completely contained within bbox2
def is_contained(bbox1, bbox2):
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2

    return (x0_1 >= x0_2 and y0_1 >= y0_2 and x1_1 <= x1_2 and y1_1 <= y1_2)

def dict_to_DB(pdf_path):
    d=extract_to_dict(pdf_path)
    file_name = pdf_path.split('/')[-1]
    pdf_document = PDFDocument.objects.create(file_name=file_name)


    for page in d:
        content_order = 0
        pdf_page = PDFPage.objects.create(
            document=pdf_document,
            page_number=page["page_number"],
            width=page["width"],
            height=page["height"],
            top_margin=page["top_margin"],
            bottom_margin=page["bottom_margin"],
        )
        for block in page["content"]:
            if block["type"] == "text":
                line_group=process_text_content(block,pdf_page)
                if line_group.lines.all():
                    PDFPageContentOrdered.objects.create(
                        page=pdf_page,
                        order=content_order,
                        line_group=line_group,
                    )
                    content_order+=1
                else:
                    line_group.delete()
            elif block["type"] == "table":
                table=process_table_content(block,pdf_page)
                PDFPageContentOrdered.objects.create(
                    page=pdf_page,
                    order=content_order,
                    table=table,
                )
                content_order+=1
            elif block["type"] == "image":
                im=PDFImage.objects.create(
                    page=pdf_page,
                    file_path=block["content"]["file_path"],
                    x=block["content"]["x"],
                    y=block["content"]["y"],
                    width=block["content"]["width"],
                    height=block["content"]["height"],
                    z_index=block["content"]["z_index"]
                )
                PDFPageContentOrdered.objects.create(
                    page=pdf_page,
                    order=content_order,
                    image=im,
                )
                content_order+=1
                # print("CAUGHT IMAGE: ", block)
    pdf_document.link_content_pageless()
    return pdf_document

def process_text_content(block,pdf_page):
    group = PDFLineGroup.objects.create(
        page=pdf_page,
        x1=block["bbox"][0],
        y1=block["bbox"][1],
        x2=block["bbox"][2],
        y2=block["bbox"][3]
    )
    group_lines = []
    for lines in block["content"]:
        for line in lines:
            # print("LINE L: ", line)
            bbox = line["bbox"]
            l = PDFText.objects.create(
                page=pdf_page,
                text=line["text"],
                x=bbox[0],
                width=bbox[2] - bbox[0],
                y=bbox[1],
                font_size=line["font_size"],
                font_weight=line["font_weight"],
                font_color=line["font_color"],
            )
            group_lines.append(l)
    group.lines.add(*group_lines)
    return group


def process_table_content(block,pdf_page):
    table=PDFTable.objects.create(
        page=pdf_page,
        x1=block["bbox"][0],
        y1=block["bbox"][1],
        x2=block["bbox"][2],
        y2=block["bbox"][3]
    )
    table_rows = []
    row_order=0
    for row in block["content"]:
        r=PDFTableRow.objects.create(
            order=row_order,
            # page=pdf_page,

        )
        table_rows.append(r)
        row_cells=[]
        row_order+=1
        cell_order=0
        for cell in row["content"]:
            db_Cell=PDFTableCell.objects.create(
                x1=cell["bbox"][0],
                y1=cell["bbox"][1],
                x2=cell["bbox"][2],
                y2=cell["bbox"][3],
                order=cell_order
            )
            cell_order+=1
            for line_l in cell["content"]:
                try:
                    line=line_l[0]
                except:
                    print("failed to get line")
                    continue
                # print(line)
                bbox = line["bbox"]
                l = PDFText.objects.create(
                page=pdf_page,
                text=line["text"],
                x=bbox[0],
                width=bbox[2] - bbox[0],
                y=bbox[1],
                font_size=line["font_size"],
                font_weight=line["font_weight"],
                font_color=line["font_color"],
            )
                print(f"PROCESSED TABLE CELL {line["text"]}")
                db_Cell.text.add(l)
                db_Cell.save()

            row_cells.append(db_Cell)
            # print(f"Adding {row_cells} to {r}")
        r.cells.add(*row_cells)
        r.save()
    table.rows.add(*table_rows)
    table.save()
    return table