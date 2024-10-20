from django.db import models

# Create your models here.
from django.db import models
from pymupdf.extra import page_count


class PDFDocument(models.Model):
    file_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    content_linked=models.BooleanField(default=False)

    def link_content_pageless(self):
        if self.content_linked:
            return
        last_bbox = None
        order = 0
        LinkModel = None
        for page in self.pages.all():
            h_threshold = page.height * 0.02
            for content in page.contents.all():
                current_bbox = content.get_merged_bbox()
                current_bbox[1]-=page.top_margin
                current_bbox[3]-=page.top_margin
                if not LinkModel:
                    LinkModel = LinkedPDFContentOrdered.objects.create(
                        document=self,
                        order=order
                    )
                    order += 1
                if not last_bbox:
                    last_bbox = current_bbox
                    LinkModel.linked_content.add(content)
                    LinkModel.save()
                    continue
                if ((current_bbox[1] - last_bbox[3]) <= h_threshold) or last_bbox[1] <= h_threshold:
                    LinkModel.linked_content.add(content)
                else:
                    LinkModel = LinkedPDFContentOrdered.objects.create(
                        document=self,
                        order=order
                    )
                    order += 1
                    LinkModel.linked_content.add(content)
                LinkModel.save()
                last_bbox = current_bbox
        self.content_linked = True
        self.save()
        return

    def get_partitioned_PDF_dict(self):
        output = {}
        output["name"]=self.file_name
        output["npages"]=self.pages.count()
        output["pages"]=[]
        output["content"]=[]
        for page in self.pages.all():
            page_dict={
                "page_number":page.page_number,
                "height":page.height,
                "width":page.width,
                "top_margin":page.top_margin,
                "bottom_margin":page.bottom_margin,
            }
            output["pages"].append(page_dict)
        for linked_content in self.linked_content.all():
            content_dict={
                "content":linked_content.get_as_txt(),
                "pages":linked_content.get_pages(),
                "link_id":linked_content.id,
            }
            output["content"].append(content_dict)
        return output



class PDFPage(models.Model):
    document = models.ForeignKey(PDFDocument, related_name='pages', on_delete=models.CASCADE)
    page_number = models.IntegerField()
    width = models.FloatField()
    height = models.FloatField()

    top_margin = models.FloatField()
    bottom_margin = models.FloatField()

class LinkedPDFContentOrdered(models.Model):
    document=models.ForeignKey("PDFDocument", on_delete=models.CASCADE, related_name="linked_content")
    linked_content=models.ManyToManyField("PDFPageContentOrdered")
    order=models.IntegerField()


    def get_as_txt(self):
        ret_txt=''''''
        for i in self.linked_content.all():
            ret_txt+=i.get_as_txt()
            ret_txt+='''\n'''
        return ret_txt

    def get_as_html(self):
        ret_txt=''''''
        for i in self.linked_content.all():
            ret_txt+='''<p>'''
            ret_txt+=i.get_as_html()
            ret_txt+='''</p>'''
        return ret_txt
    def get_pages(self):
        pages=[]
        for i in self.linked_content.all():
            if i.page.page_number not in pages:
                pages.append(i.page.page_number)
        return pages

class PDFPageContentOrdered(models.Model):
    page = models.ForeignKey(PDFPage, related_name='contents', on_delete=models.CASCADE)
    line_group=models.ForeignKey("PDFLineGroup", null=True, blank=True, on_delete=models.CASCADE)
    image=models.ForeignKey("PDFImage", null=True, blank=True, on_delete=models.CASCADE)
    table=models.ForeignKey("PDFTable", null=True, blank=True, on_delete=models.CASCADE)
    order=models.IntegerField()

    def get_as_txt(self):
        if self.line_group:
            return self.line_group.get_as_txt()
        elif self.table:
            return self.table.get_as_txt()
        return ""
    def get_as_html(self):
        if self.line_group:
            return self.line_group.get_as_html()

        return ""
    class Meta:
        ordering = ('page','order',)

    def get_merged_bbox(self):
        x1=None
        y1=None
        x2=None
        y2=None
        if self.line_group:
            if not x1:
                x1=self.line_group.x1
            elif self.line_group.x1<x1:
                x1=self.line_group.x1
            if not y1:
                y1=self.line_group.y1
            elif self.line_group.y1<y1:
                y1=self.line_group.y1
            if not x2:
                x2=self.line_group.x2
            elif self.line_group.x2>x2:
                x2=self.line_group.x2
            if not y2:
                y2=self.line_group.y2
            elif self.line_group.y2>y2:
                y2=self.line_group.y2
        if self.table:
            if not x1:
                x1=self.table.x1
            elif self.table.x1<x1:
                x1=self.table.x1
            if not y1:
                y1=self.table.y1
            elif self.table.y1<y1:
                y1=self.table.y1
            if not x2:
                x2=self.table.x2
            elif self.table.x2>x2:
                x2=self.table.x2
            if not y2:
                y2=self.table.y2
            elif self.table.y2>y2:
                y2=self.table.y2

        if self.image:
            if not x1:
                x1=self.image.x
            elif self.image.x<x1:
                x1=self.image.x
            if not y1:
                y1=self.image.y
            elif self.image.y<y1:
                y1=self.image.y
            if not x2:
                x2=self.image.x + self.image.width
            elif (self.image.x + self.image.width) > x2:
                x2=self.image.x + self.image.width
            if not y2:
                y2=self.image.y+self.image.height
            elif (self.image.y+self.image.height)>y2:
                y2=self.image.y+self.image.height
        return [x1,y1,x2,y2]

class PDFImage(models.Model):
    page = models.ForeignKey(PDFPage, related_name='images', on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    z_index = models.IntegerField()


class PDFText(models.Model):
    page = models.ForeignKey(PDFPage, related_name='texts', on_delete=models.CASCADE)
    text = models.TextField()
    x = models.FloatField()
    width=models.FloatField(default=100)
    y = models.FloatField()
    font_size = models.FloatField()
    font_weight = models.CharField(max_length=50)
    font_color = models.CharField(max_length=20)
    order=models.IntegerField(default=0)

    def rev_x(self):
        return 0-self.x
    def rev_y(self):
        return 0-self.y

    class Meta:
        ordering = ('order',)
class PDFLineGroup(models.Model):
    page = models.ForeignKey(PDFPage, on_delete=models.CASCADE)
    x1= models.FloatField()
    y1= models.FloatField()
    x2= models.FloatField()
    y2= models.FloatField()
    lines = models.ManyToManyField(PDFText)

    def get_width(self):
        return self.x2-self.x1

    def get_height(self):
        return self.y2-self.y1
    def get_as_html(self):
        ret_txt=''''''
        for i in self.lines.all():
            ret_txt+=i.text+" "
        return ret_txt

    def get_as_txt(self):
        ret_txt=''''''
        for i in self.lines.all():
            ret_txt+=i.text+" "
        return ret_txt

class PDFTable(models.Model):
    page = models.ForeignKey(PDFPage, on_delete=models.CASCADE)
    x1= models.FloatField()
    y1= models.FloatField()
    x2= models.FloatField()
    y2= models.FloatField()
    # nrows=models.IntegerField()
    # ncols=models.IntegerField()
    # header=models.OneToOneField("PDFTableHeader", on_delete=models.CASCADE)
    rows=models.ManyToManyField("PDFTableRow", related_name='parent')

    def get_as_txt(self):
        ret_txt=''''''
        for row in self.rows.all():
            ret_txt+=row.get_as_txt()+"\n"
        return ret_txt

class PDFTableCell(models.Model):
    text=models.ManyToManyField(PDFText)
    x1= models.FloatField()
    y1= models.FloatField()
    x2= models.FloatField()
    y2= models.FloatField()
    order=models.IntegerField(default=0)
    class Meta:
        ordering = ('order',)
    def get_as_txt(self):
        ret_text=''''''
        for t in self.text.all():
            ret_text+=t.text+" "
        return ret_text
class PDFTableHeader(models.Model):
    cells=models.ManyToManyField(PDFTableCell)

class PDFTableRow(models.Model):
    cells=models.ManyToManyField(PDFTableCell)
    order=models.IntegerField(default=0)

    def get_as_txt(self):
        ret_txt=''''''
        for cell in self.cells.all():
            ret_txt+=cell.get_as_txt()+" -;- "
        return ret_txt

    class Meta:
        ordering = ('order',)

