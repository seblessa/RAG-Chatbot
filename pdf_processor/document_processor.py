import fitz  # PyMuPDF

def remove_unwanted_fields(data):
    # Lista de campos que devem ser removidos
    unwanted_fields = ['bbox', 'x', 'width', 'y', 'font_size', 'font_weight', 'font_color']

    if isinstance(data, list):
        # Se for uma lista, percorre cada item da lista
        return [remove_unwanted_fields(item) for item in data]
    elif isinstance(data, dict):
        # Se for um dicionário, remove os campos indesejados e continua processando os valores
        return {key: remove_unwanted_fields(value) for key, value in data.items() if key not in unwanted_fields}
    else:
        # Se não for nem lista nem dicionário, retorna o valor original
        return data

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
        pdf_content=remove_unwanted_fields(pdf_content)

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

