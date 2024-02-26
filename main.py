# -------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
# -------------------------------------------------------------------------------
# from __future__ import division
from tkinter import *
from PIL import Image, ImageTk
import os
import glob
from google.cloud import firestore
from google.cloud import storage
from datetime import datetime, timedelta
from configs import BUCKET_NAME, IMAGE_DIR, LABELS, DAYS_BACK, OUT_DIR, QUERY_THRESHOLD, YOLO_OUT_DIR
# colors for the bboxes
COLORS = ["red", "blue", "cyan", "green", "black"]


def convert(size, box):
    image_width = size[0]
    image_height = size[1]
    # Unpack the bounding box coordinates
    cls, x_min, y_min, x_max, y_max = box

    # Calculate the center coordinates of the bounding box
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2

    # Calculate the width and height of the bounding box
    width = x_max - x_min
    height = y_max - y_min

    # Normalize the coordinates and dimensions
    x_center /= image_width
    y_center /= image_height
    width /= image_width
    height /= image_height

    return (cls, x_center, y_center, width, height)


class LabelTool:
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=FALSE, height=FALSE)

        # initialize global state
        self.imageDir = os.path.join(IMAGE_DIR)
        self.imageList = []
        self.outDir = os.path.join(OUT_DIR)
        self.yoloOutDir = os.path.join(YOLO_OUT_DIR)
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ""
        self.labelfilename = ""
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE["click"] = 0
        self.STATE["x"], self.STATE["y"] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.yoloBoxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        # self.label = Label(self.frame, text="Image Dir:")
        # self.label.grid(row=0, column=0, sticky=E)
        # self.entry = Entry(self.frame)
        # self.entry.grid(row=0, column=1, sticky=W + E)

        self.dldBtn = Button(self.frame, text="Download", command=self.downloadImages)
        self.dldBtn.grid(row=0, column=1, sticky=E)

        self.ldBtn = Button(self.frame, text="Load", command=self.loadDir)
        self.ldBtn.grid(row=0, column=2, sticky=W + E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor="tcross")
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind(
            "<Escape>", self.cancelBBox
        )  # press <Espace> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage)  # press 'a' to go backforward
        self.parent.bind("d", self.nextImage)  # press 'd' to go forward
        self.mainPanel.grid(row=1, column=1, rowspan=8, sticky=W + N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text="Bounding boxes:")
        self.lb1.grid(row=1, column=2, sticky=W + N)
        self.listbox = Listbox(self.frame, width=22, height=12)
        self.listbox.grid(row=2, column=2, sticky=N)
        self.btnDel = Button(self.frame, text="Delete", command=self.delBBox)
        self.btnDel.grid(row=3, column=2, sticky=W + E + N)
        self.btnClear = Button(self.frame, text="ClearAll", command=self.clearBBox)
        self.btnClear.grid(row=5, column=2, sticky=W + E + N)
        # Getting the labels on display
        self.listboxOption = Listbox(self.frame, width=22, height=32)
        [self.listboxOption.insert(x, y) for x, y in LABELS.items()]
        self.listboxOption.grid(row=6, column=2, sticky=N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=9, column=1, columnspan=2, sticky=W + E)
        self.prevBtn = Button(
            self.ctrPanel, text="<< Prev", width=10, command=self.prevImage
        )
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(
            self.ctrPanel, text="Save & Next >>", width=14, command=self.nextImage
        )
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)

        # Skip Button Start
        self.nextBtn = Button(
            self.ctrPanel, text="Skip >>", width=10, command=self.skip_image
        )
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        # Skip Button ends

        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text="Go", command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # # example pannel for illustration
        # self.egPanel = Frame(self.frame, border = 10)
        # self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        # self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        # self.tmpLabel2.pack(side = TOP, pady = 5)
        # self.egLabels = []
        # for i in range(3):
        #     self.egLabels.append(Label(self.egPanel))
        #     self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text="")
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

    def loadDir(self):
        # get image list
        self.imageDir = os.path.join(IMAGE_DIR)
        self.imageList = glob.glob(os.path.join(self.imageDir, "*"))
        # print self.imageList
        if len(self.imageList) == 0:
            print("No images found in the specified dir!")
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        if not os.path.exists(self.yoloOutDir):
            os.mkdir(self.yoloOutDir)

        self.loadImage()
        print(f"{self.total} images loaded from {self.imageDir}")

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.imgsize = self.img.size
        self.mainPanel.config(
            width=max(self.tkimg.width(), 400), height=max(self.tkimg.height(), 400)
        )
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=NW)
        self.progLabel.config(text="%04d/%04d" % (self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split(".")[0]
        labelname = self.imagename + ".txt"
        self.labelfilename = os.path.join(self.outDir, labelname)
        # Need to figure out how I want yolo labels
        self.yololabelfilename = os.path.join(self.yoloOutDir, labelname)

        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for i, line in enumerate(f):
                    tmp = [int(t.strip()) for t in line.split()]
                    self.bboxList.append(tuple(tmp))
                    self.yoloBoxList.append(convert(self.imgsize, tmp))

                    tmpId = self.mainPanel.create_rectangle(
                        tmp[1],
                        tmp[2],
                        tmp[3],
                        tmp[4],
                        width=2,
                        outline=COLORS[(len(self.bboxList) - 1) % len(COLORS)],
                    )
                    selection = self.get_label_value(tmp[0])
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(
                        END,
                        "%s : (%d, %d) -> (%d, %d)"
                        % (selection, tmp[1], tmp[2], tmp[3], tmp[4]),
                    )
                    self.listbox.itemconfig(
                        len(self.bboxIdList) - 1,
                        fg=COLORS[(len(self.bboxIdList) - 1) % len(COLORS)],
                    )
        # print(self.bboxList)
        # print(self.yoloBoxList)

    def saveImage(self):
        with open(self.labelfilename, "w") as f:
            for bbox in self.bboxList:
                f.write(" ".join(map(str, bbox)) + "\n")
        with open(self.yololabelfilename, "w") as f:
            for yolobbox in self.yoloBoxList:
                f.write(" ".join(map(str, yolobbox)) + "\n")
        print(f"Image {self.cur}'s box saved")

    def mouseClick(self, event):
        if self.STATE["click"] == 0:
            self.STATE["x"], self.STATE["y"] = event.x, event.y
        else:
            x1, x2 = min(self.STATE["x"], event.x), max(self.STATE["x"], event.x)
            y1, y2 = min(self.STATE["y"], event.y), max(self.STATE["y"], event.y)
            selection = self.listboxOption.get(self.listboxOption.curselection())
            self.bboxList.append((self.get_index(selection), x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            print(self.bboxList)
            self.bboxId = None
            self.listbox.insert(
                END, "%s : (%d, %d) -> (%d, %d)" % (selection, x1, y1, x2, y2)
            )
            self.listbox.itemconfig(
                len(self.bboxIdList) - 1,
                fg=COLORS[(len(self.bboxIdList) - 1) % len(COLORS)],
            )
        self.STATE["click"] = 1 - self.STATE["click"]

    def mouseMove(self, event):
        self.disp.config(text="x: %d, y: %d" % (event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(
                0, event.y, self.tkimg.width(), event.y, width=2
            )
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(
                event.x, 0, event.x, self.tkimg.height(), width=2
            )
        if 1 == self.STATE["click"]:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(
                self.STATE["x"],
                self.STATE["y"],
                event.x,
                event.y,
                width=2,
                outline=COLORS[len(self.bboxList) % len(COLORS)],
            )

    def cancelBBox(self, event):
        if 1 == self.STATE["click"]:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE["click"] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []
        self.yoloBoxList = []

    def prevImage(self, event=None):
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def skip_image(self, event=None):
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    # Custom method for getting index
    def get_index(self, value):
        for key, label in LABELS.items():
            if value == label:
                return key

    def get_label_value(self, index):
        try:
            return LABELS[index]
        except:
            return None

    def get_date(self):
        today = datetime.today()
        target_date = today - timedelta(days=DAYS_BACK)
        formatted_date = target_date.strftime('%Y-%m-%d')
        return formatted_date

    def downloadImages(self):
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        loading_popup = Tk()
        loading_popup.geometry("200x100")
        loading_popup.title("Downloading Images...")

        progress_label = Label(loading_popup, text="Downloading...")
        progress_label.pack()

        loading_popup.update_idletasks()

    def download_helper(self, bucket, image_filename):
        image_local_path = os.path.join(IMAGE_DIR, image_filename)

        if os.path.exists(image_local_path):
            print(f"{image_local_path} already exists")
            return True
        blob = storage.Blob(image_filename, bucket)

        if blob.exists():
            blob.download_to_filename(image_local_path)
            return True
        return False

    def gcp_query_download(self):
        db = firestore.Client()
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(BUCKET_NAME)
        sightings_ref = db.collection("sightings")

        image_count = 0

        query_date_from = self.get_date()
        query = sightings_ref.where(filter=firestore.FieldFilter("date", ">=", query_date_from))
        query = sightings_ref.where(filter=firestore.FieldFilter("is_processed_any_positive", "==", True))

        # Check for is_labelled -> this will be set to true after the image has been labelled
        query = sightings_ref.where(filter=firestore.FieldFilter("is_labelled", "!=", True))
        if QUERY_THRESHOLD:
            query = query.limit(QUERY_THRESHOLD)

        sightings_docs = query.get()

        for doc in sightings_docs:
            try:
                doc_data = doc.to_dict()
                sighting_id = doc_data.get("sighting_id")
                taken_on = doc_data.get("taken_on")
                date = doc_data.get("date")
                time = doc_data.get("time")

                face_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_FACE.jpg"
                wscr_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_WSCR.jpg"
                # lp_image_name = f"{sighting_id}_{taken_on}_{date}_{time}_LP.jpg"

                self.download_helper(bucket, face_image_name)
                self.download_helper(bucket, wscr_image_name)

            except Exception as e:
                print(f"Error downloading images for sighting {sighting_id}, {e}")
                continue

if __name__ == "__main__":
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
