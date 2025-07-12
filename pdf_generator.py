# pic_to_pdf_gui.py
import os
import sys
from pathlib import Path
from PIL import Image
import subprocess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QMessageBox, QCheckBox
)

# ==== 打包后资源路径支持（MEIPASS） ====
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    os.environ["PATH"] += os.pathsep + str(BASE_DIR / "vendor" / "gs")
    os.environ["PATH"] += os.pathsep + str(BASE_DIR / "vendor" / "poppler")
    POPPLER_DIR = str(BASE_DIR / "vendor" / "poppler")
else:
    POPPLER_DIR = None

from pdf2image import convert_from_path

try:
    import pikepdf
except ImportError:
    pikepdf = None


class DraggableListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Generator(made by lyh)")
        self.setMinimumWidth(600)
        self.setWindowIcon(QIcon.fromTheme("application-pdf"))

        self.list_widget = DraggableListWidget()
        add_btn =   QPushButton("➕ 添加文件", clicked=self.add_files)
        rm_btn =    QPushButton("❌ 移除选中", clicked=self.remove_selected)
        clear_btn = QPushButton("🗑 清空列表", clicked=self.list_widget.clear)

        self.compress_chk = QCheckBox("压缩输出")
        self.compress_chk.setChecked(False)

        merge_btn = QPushButton("📄 生成 PDF", clicked=self.merge_to_pdf)
        merge_btn.setStyleSheet("font-weight:bold;padding:8px;")

        side = QVBoxLayout()
        for w in (add_btn, rm_btn, clear_btn, QLabel(""), self.compress_chk, merge_btn):
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
            pages = self._load_pages()
            if not pages:
                raise RuntimeError("无有效页面！")
            pages[0].save(out_path, save_all=True, append_images=pages[1:])
            if self.compress_chk.isChecked():
                self._compress_pdf(out_path)
            QMessageBox.information(self, "完成", f"PDF 已保存：{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _load_pages(self):
        result, target_size = [], None
        for i in range(self.list_widget.count()):
            path = self.list_widget.item(i).text()
            ext = Path(path).suffix.lower()
            if ext in {".png", ".jpg", ".jpeg"}:
                img = Image.open(path).convert("RGB")
                target_size = target_size or img.size
                result.append(img.resize(target_size, Image.Resampling.LANCZOS))
            elif ext == ".pdf":
                pdf_pages = convert_from_path(
                    path, dpi=200,
                    poppler_path=POPPLER_DIR if POPPLER_DIR else None
                )
                for pg in pdf_pages:
                    pg = pg.convert("RGB")
                    target_size = target_size or pg.size
                    result.append(pg.resize(target_size, Image.Resampling.LANCZOS))
            else:
                print("跳过:", path)
        return result

    def _compress_pdf(self, path):
        if pikepdf:
            try:
                with pikepdf.open(path) as pdf:
                    pdf.save(path, optimize_streams=True, linearize=True)
            except Exception:
                pass

        gs = "gswin64c" if os.name == "nt" else "gs"
        tmp = path + ".tmp"
        cmd = [
            gs, "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE", "-dBATCH",
            f"-sOutputFile={tmp}", path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
