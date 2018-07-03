#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
#-------------------------------------------------------------------------------
from __future__ import division
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import os
import glob
import random

# colors for the bboxes
Extension = '.ppm'
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
labels = {
0 : 'speed limit 20 (prohibitory)',
1 : 'speed limit 30 (prohibitory)',
2 : 'speed limit 50 (prohibitory)',
3 : 'speed limit 60 (prohibitory)',
4 : 'speed limit 70 (prohibitory)',
5 : 'speed limit 80 (prohibitory)',
6 : 'restriction ends 80 (other)',
7 : 'speed limit 100 (prohibitory)',
8 : 'speed limit 120 (prohibitory)',
9 : 'no overtaking (prohibitory)',
10 : 'no overtaking (trucks) (prohibitory)',
11 : 'priority at next intersection (danger)',
12 : 'priority road (other)',
13 : 'give way (other)',
14 : 'stop (other)',
15 : 'no traffic both ways (prohibitory)',
16 : 'no trucks (prohibitory)',
17 : 'no entry (other)',
18 : 'danger (danger)',
19 : 'bend left (danger)',
20 : 'bend right (danger)',
21 : 'bend (danger)',
22 : 'uneven road (danger)',
23 : 'slippery road (danger)',
24 : 'road narrows (danger)',
25 : 'construction (danger)',
26 : 'traffic signal (danger)',
27 : 'pedestrian crossing (danger)',
28 : 'school crossing (danger)',
29 : 'cycles crossing (danger)',
30 : 'snow (danger)',
31 : 'animals (danger)',
32 : 'restriction ends (other)',
33 : 'go right (mandatory)',
34 : 'go left (mandatory)',
35 : 'go straight (mandatory)',
36 : 'go right or straight (mandatory)',
37 : 'go left or straight (mandatory)',
38 : 'keep right (mandatory)',
39 : 'keep left (mandatory)',
40 : 'roundabout (mandatory)',
41 : 'restriction ends (overtaking) (other)',
42 : 'restriction ends (overtaking (trucks)) (other)'
}
# image sizes for the examples
SIZE = 256, 256

class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2, sticky = W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 8, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 1, column = 2,  sticky = W+N)
        self.listbox = Listbox(self.frame, width = 22, height = 12)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 5, column = 2, sticky = W+E+N)
        #Getting the labels on display
        self.listboxOption = Listbox(self.frame,width = 22, height = 32)
        [self.listboxOption.insert(x,y) for x,y in labels.items()]
        self.listboxOption.grid(row = 6, column = 2, sticky = N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 9, column = 1, columnspan = 2, sticky = W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Save & Next >>', width = 14, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)

        #Skip Button Start
        self.nextBtn = Button(self.ctrPanel, text='Skip >>', width=10, command=self.skip_image)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        #Skip Button ends

        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border = 10)
        self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        self.tmpLabel2.pack(side = TOP, pady = 5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

    def loadDir(self, dbg = False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = int(s)
        else:
            s = r'D:\workspace\python\labelGUI'
        # get image list
        self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        #print self.imageDir
        self.imageList = glob.glob(os.path.join(self.imageDir, '*'+Extension))
        #print self.imageList 
        if len(self.imageList) == 0:
            print ('No ',Extension,' images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        self.outDir = os.path.join(r'./Labels', '%03d' %(self.category))
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        # load example bboxes
        self.egDir = os.path.join(r'./Examples', '%03d' %(self.category))
        if not os.path.exists(self.egDir):
            print ("exiting, no examples")
            return
        filelist = glob.glob(os.path.join(self.egDir, '*'+Extension))
        self.tmp = []
        self.egList = []
        random.shuffle(filelist)
        print("execution reached")
        for (i, f) in enumerate(filelist):
            if i == 3:
                break
            im = Image.open(f)
            print ("opened ",im)
            r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
            new_size = int(r * im.size[0]), int(r * im.size[1])
            self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
            self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
            self.egLabels[i].config(image = self.egList[-1], width = SIZE[0], height = SIZE[1])

        self.loadImage()
        print ('%d images loaded from %s' %(self.total, s))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        #print "imagename is ",self.imagename
        #print "labelname is", labelname
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    if i == 0:
                        bbox_cnt = int(line.strip())
                        continue
                    tmp = [int(t.strip()) for t in line.split()]
##                    print tmp
                    self.bboxList.append(tuple(tmp))
                    tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1], \
                                                            tmp[2], tmp[3], \
                                                            width = 2, \
                                                            outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(tmp[0], tmp[1], tmp[2], tmp[3]))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])

    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            for bbox in self.bboxList:
                f.write(' '.join(map(str, bbox)) + '\n')
        #Save the current image in the new flder as well
        self.imagefilename = os.path.join(self.outDir, self.imagename)
        print ('original file name is ', self.imagename)
        print ('new file name is ',self.imagefilename)
        with open(self.imagefilename + Extension, 'w') as f:
            self.img.save(f)
        #Delete file
        try:
            remove_name = os.path.join(self.imageDir, self.imagename + Extension)
            os.remove(remove_name)
        except:
            print ('please skip')
        print ('Image No. %d saved' %(self.cur))


    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            selection = self.listboxOption.get(self.listboxOption.curselection())
            self.bboxList.append((self.get_index(selection), x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' %(selection, x1, y1, x2, y2 ))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxList) % len(COLORS)])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
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

    def prevImage(self, event = None):
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def skip_image(self, event = None):
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()
    #Custom method for getting index
    def get_index(self, value):
        for key,label in labels.items():
            if value == label:
                return key


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width =  True, height = True)
    root.mainloop()
