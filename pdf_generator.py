import os
import sys
from pathlib import Path
from PIL import Image
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QMessageBox,
    QCheckBox, QProgressBar, QSpinBox
)

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    os.environ["PATH"] += os.pathsep + str(BASE_DIR / "vendor" / "gs")
    os.environ["PATH"] += os.pathsep + str(BASE_DIR / "vendor" / "poppler")
    POPPLER_DIR = str(BASE_DIR / "vendor" / "poppler")
else:
    POPPLER_DIR = None

from pdf2image import convert_from_path

class DraggableListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
                    self.addItem(path)
        else:
            super().dropEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Generator (made by lyh)")
        self.setMinimumWidth(650)
        self.setWindowIcon(QIcon.fromTheme("application-pdf"))

        self.list_widget = DraggableListWidget()
        add_btn = QPushButton("➕ 添加文件", clicked=self.add_files)
        rm_btn = QPushButton("❌ 移除选中", clicked=self.remove_selected)
        clear_btn = QPushButton("🗑 清空列表", clicked=self.list_widget.clear)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(1024)
        self.width_spin.setSuffix(" px")

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setValue(0)

        merge_btn = QPushButton("📄 生成 PDF", clicked=self.merge_to_pdf)
        merge_btn.setStyleSheet("font-weight:bold;padding:8px;")

        side = QVBoxLayout()
        for w in (add_btn, rm_btn, clear_btn,
                  QLabel("目标宽度 (px):"), self.width_spin,
                  QLabel("进度："), self.progress,
                  merge_btn):
            side.addWidget(w)
        side.addStretch()

        layout = QHBoxLayout()
        layout.addWidget(self.list_widget, 3)
        container = QWidget(); container.setLayout(side)
        layout.addWidget(container, 1)
        central = QWidget(); central.setLayout(layout)
        self.setCentralWidget(central)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片或 PDF", "", "Images/PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        for f in files:
            self.list_widget.addItem(QListWidgetItem(f))

    def remove_selected(self):
        for it in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(it))

    def merge_to_pdf(self):
        if self.list_widget.count() == 0:
            QMessageBox.warning(self, "列表为空", "请先添加文件！")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", "output.pdf", "PDF (*.pdf)"
        )
        if not out_path:
            return

        try:
            total_pages = 0
            for i in range(self.list_widget.count()):
                path = self.list_widget.item(i).text()
                ext = Path(path).suffix.lower()
                if ext in {".png", ".jpg", ".jpeg"}:
                    total_pages += 1
                elif ext == ".pdf":
                    pdf_imgs = convert_from_path(path, dpi=10, poppler_path=POPPLER_DIR)
                    total_pages += len(pdf_imgs)

            self.progress.setMaximum(total_pages)
            self.progress.setValue(0)

            pages = self._load_pages()
            if not pages:
                raise RuntimeError("无有效页面！")

            pages[0].save(out_path, save_all=True, append_images=pages[1:])
            QMessageBox.information(self, "完成", f"PDF 已保存：{out_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
        finally:
            self.progress.setValue(0)

    def _load_pages(self):
        result = []
        target_width = self.width_spin.value()
        page_counter = 0

        for i in range(self.list_widget.count()):
            path = self.list_widget.item(i).text()
            ext = Path(path).suffix.lower()
            if ext in {".png", ".jpg", ".jpeg"}:
                img = Image.open(path).convert("RGB")
                w_percent = target_width / img.width
                new_height = int(img.height * w_percent)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                result.append(img)
                page_counter += 1
                self.progress.setValue(page_counter)

            elif ext == ".pdf":
                pdf_pages = convert_from_path(
                    path, dpi=200,
                    poppler_path=POPPLER_DIR if POPPLER_DIR else None
                )
                for pg in pdf_pages:
                    pg = pg.convert("RGB")
                    w_percent = target_width / pg.width
                    new_height = int(pg.height * w_percent)
                    pg = pg.resize((target_width, new_height), Image.Resampling.LANCZOS)
                    result.append(pg)
                    page_counter += 1
                    self.progress.setValue(page_counter)

        return result

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
