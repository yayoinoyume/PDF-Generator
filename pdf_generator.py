# -*- coding: utf-8 -*-
"""
PDF Generator - 图片和PDF文件合并工具
主窗口模块，提供拖拽界面和文件处理功能
"""

import os
import sys
import warnings
from pathlib import Path
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QMessageBox,
    QCheckBox, QProgressBar, QSpinBox
)

# 抑制PIL和libpng的警告信息
warnings.filterwarnings('ignore', category=UserWarning, module='PIL')
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning:PIL'
# 抑制libpng警告（通过环境变量）
os.environ['LIBPNG_WARNINGS'] = '0'

from worker_thread import PDFProcessWorker

# 配置打包后的环境变量
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    vendor_dir = BASE_DIR / "vendor"
    os.environ["PATH"] += os.pathsep + str(vendor_dir)
    POPPLER_DIR = str(vendor_dir)
else:
    POPPLER_DIR = None

from pdf2image import convert_from_path

class DraggableListWidget(QListWidget):
    """支持拖拽和排序的文件列表组件"""
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        """处理文件拖放事件"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
                    self.addItem(path)
        else:
            super().dropEvent(event)

class MainWindow(QMainWindow):
    """主窗口类，提供PDF生成器的用户界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Generator (made by lyh)")
        self.setMinimumWidth(650)
        self.setWindowIcon(QIcon.fromTheme("application-pdf"))
        
        # 工作线程实例
        self.worker = None

        self.list_widget = DraggableListWidget()
        add_btn = QPushButton("➕ 添加文件", clicked=self.add_files)
        rm_btn = QPushButton("❌ 移除选中", clicked=self.remove_selected)
        clear_btn = QPushButton("🗑 清空列表", clicked=self.list_widget.clear)

        # 图片宽度设置
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(1024)
        self.width_spin.setSuffix(" px")

        # 压缩选项控件
        self.compress_checkbox = QCheckBox("启用压缩")
        self.compress_checkbox.setChecked(True)
        
        self.compression_quality_label = QLabel("压缩质量:")
        self.compression_quality_spin = QSpinBox()
        self.compression_quality_spin.setRange(1, 100)
        self.compression_quality_spin.setValue(85)
        self.compression_quality_spin.setSuffix(" %")
        
        # 压缩质量控件与复选框联动
        self.compress_checkbox.toggled.connect(self.compression_quality_spin.setEnabled)
        self.compression_quality_spin.setEnabled(True)

        # 进度显示控件
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setValue(0)
        
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)

        # 操作按钮
        self.merge_btn = QPushButton("📄 生成 PDF", clicked=self.merge_to_pdf)
        self.merge_btn.setStyleSheet("font-weight:bold;padding:8px;")
        
        self.cancel_btn = QPushButton("⏹ 取消操作", clicked=self.cancel_operation)
        self.cancel_btn.setStyleSheet("padding:8px;")
        self.cancel_btn.setEnabled(False)

        side = QVBoxLayout()
        for w in (add_btn, rm_btn, clear_btn,
                  QLabel("目标宽度 (px):"), self.width_spin,
                  self.compress_checkbox,
                  self.compression_quality_label, self.compression_quality_spin,
                  QLabel("进度："), self.progress, self.status_label,
                  self.merge_btn, self.cancel_btn):
            side.addWidget(w)
        side.addStretch()

        layout = QHBoxLayout()
        layout.addWidget(self.list_widget, 3)
        container = QWidget(); container.setLayout(side)
        layout.addWidget(container, 1)
        central = QWidget(); central.setLayout(layout)
        self.setCentralWidget(central)

    def add_files(self):
        """添加文件到列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片或 PDF", "", "Images/PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        for f in files:
            self.list_widget.addItem(QListWidgetItem(f))

    def remove_selected(self):
        """移除选中的文件"""
        for it in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(it))

    def merge_to_pdf(self):
        """启动PDF生成过程"""
        if self.list_widget.count() == 0:
            QMessageBox.warning(self, "列表为空", "请先添加文件！")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", "output.pdf", "PDF (*.pdf)"
        )
        if not out_path:
            return
            
        # 更新界面状态
        self.merge_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 重置进度条
        self.progress.setValue(0)
        self.progress.setMaximum(0)
        self.progress.setFormat("0%")
        
        # 收集文件路径
        file_paths = []
        for i in range(self.list_widget.count()):
            file_paths.append(self.list_widget.item(i).text())

        # 创建并配置工作线程
        self.worker = PDFProcessWorker(
            file_paths=file_paths,
            output_path=out_path,
            width=self.width_spin.value(),
            poppler_dir=POPPLER_DIR,
            dpi=200,
            compress=self.compress_checkbox.isChecked(),
            compression_quality=self.compression_quality_spin.value()
        )
        
        # 连接信号
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.progress_range_updated.connect(self.set_progress_range)
        self.worker.processing_finished.connect(self.on_processing_finished)
        self.worker.start()
        
    def set_progress_range(self, total_steps):
        """设置进度条范围"""
        self.progress.setMaximum(total_steps)
        if total_steps > 0:
            percentage = int((self.progress.value() / total_steps) * 100)
            self.progress.setFormat(f"{percentage}%")
        
    def update_progress(self, value, message):
        """更新进度显示"""
        self.status_label.setText(message)
        self.progress.setValue(value)
        
        if self.progress.maximum() > 0:
            percentage = int((value / self.progress.maximum()) * 100)
            self.progress.setFormat(f"{percentage}%")
        
    def on_processing_finished(self, success, message):
        """处理完成回调"""
        # 恢复界面状态
        self.merge_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)
            
        # 重置显示状态
        self.progress.setValue(0)
        self.status_label.setText("就绪")
        self.worker = None
        
    def cancel_operation(self):
        """取消当前操作"""
        if self.worker and self.worker.isRunning():
            self.status_label.setText("正在取消...")
            self.worker.cancel()


def main():
    """程序入口函数"""
    try:
        # 添加错误日志记录
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('app_debug.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logging.info("程序启动中...")
        
        # 检查关键依赖
        try:
            from pdf2image import convert_from_path
            logging.info("pdf2image导入成功")
        except Exception as e:
            logging.error(f"pdf2image导入失败: {e}")
            raise
            
        try:
            import pikepdf
            logging.info(f"pikepdf导入成功，版本: {pikepdf.__version__}")
        except Exception as e:
            logging.error(f"pikepdf导入失败: {e}")
            raise
        
        # 检查vendor目录
        if getattr(sys, 'frozen', False):
            BASE_DIR = Path(sys._MEIPASS)
            vendor_dir = BASE_DIR / "vendor"
            logging.info(f"运行环境: 打包模式，vendor目录: {vendor_dir}")
            logging.info(f"vendor目录存在: {vendor_dir.exists()}")
            if vendor_dir.exists():
                vendor_files = list(vendor_dir.glob('*.exe'))
                logging.info(f"vendor目录中的exe文件: {[f.name for f in vendor_files]}")
        else:
            logging.info("运行环境: 开发模式")
        
        app = QApplication(sys.argv)
        logging.info("QApplication创建成功")
        
        win = MainWindow()
        logging.info("MainWindow创建成功")
        
        win.show()
        logging.info("窗口显示成功")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        error_msg = f"程序启动失败: {str(e)}"
        print(error_msg)
        
        # 尝试记录到文件
        try:
            with open('startup_error.log', 'w', encoding='utf-8') as f:
                import traceback
                f.write(f"启动错误: {error_msg}\n")
                f.write(f"详细错误信息:\n{traceback.format_exc()}")
        except:
            pass
            
        # 显示错误对话框（如果可能）
        try:
            from PyQt5.QtWidgets import QMessageBox
            if not QApplication.instance():
                error_app = QApplication(sys.argv)
            QMessageBox.critical(None, "启动错误", error_msg)
        except:
            pass
            
        sys.exit(1)

if __name__ == "__main__":
    main()
