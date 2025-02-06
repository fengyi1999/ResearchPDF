import sys
import os
from pathlib import Path
from typing import List
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QTextEdit,
                           QLabel, QFileDialog, QScrollArea, QFrame,
                           QProgressBar, QMenu)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCursor
import webbrowser
from .core import PDFProcessor

class SearchWorker(QThread):
    """搜索工作线程"""
    finished = pyqtSignal(dict)  # 发送搜索结果信号
    
    def __init__(self, processor, query):
        super().__init__()
        self.processor = processor
        self.query = query
        
    def run(self):
        results = self.processor.search(self.query)
        self.finished.emit(results)

class IndexWorker(QThread):
    """索引工作线程"""
    finished = pyqtSignal()
    progress = pyqtSignal(float)
    
    def __init__(self, processor, directory):
        super().__init__()
        self.processor = processor
        self.directory = directory
        
    def run(self):
        self.processor.index_directory(self.directory, self.progress.emit)
        self.finished.emit()

class ResultWidget(QFrame):
    """搜索结果显示组件"""
    def __init__(self, file_path: str, page_numbers: List[int]):
        super().__init__()
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout()
        
        # 文件名（作为链接）
        file_label = QPushButton(Path(file_path).name)
        file_label.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: none;
                color: blue;
                text-decoration: underline;
                background: transparent;
            }
            QPushButton:hover {
                color: darkblue;
            }
        """)
        file_label.setCursor(QCursor(Qt.PointingHandCursor))
        file_label.clicked.connect(lambda: self.open_file(file_path))
        layout.addWidget(file_label)
        
        # 页码列表
        page_numbers_str = ", ".join(str(p) for p in page_numbers)
        page_label = QLabel(f"页码: {page_numbers_str}")
        page_label.setIndent(20)
        layout.addWidget(page_label)
        
        self.setLayout(layout)
        
    def open_file(self, file_path):
        """打开PDF文件"""
        try:
            webbrowser.open(file_path)
        except Exception as e:
            print(f"打开文件失败: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processor = PDFProcessor()
        self.init_ui()
        
    def update_title(self):
        """更新窗口标题"""
        base_title = 'PDF全文检索工具'
        current_dir = self.processor.get_current_directory()
        if current_dir:
            self.setWindowTitle(f'{base_title} - {current_dir}')
        else:
            self.setWindowTitle(base_title)

    def init_ui(self):
        """初始化用户界面"""
        self.update_title()
        self.setGeometry(100, 100, 800, 600)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        
        # 目录选择
        self.dir_button = QPushButton('选择目录')
        self.dir_button.clicked.connect(self.select_directory)
        self.dir_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_button.customContextMenuRequested.connect(self.show_history_menu)
        control_layout.addWidget(self.dir_button)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入搜索关键词...')
        self.search_input.returnPressed.connect(self.start_search)
        control_layout.addWidget(self.search_input)
        
        # 搜索按钮
        self.search_button = QPushButton('搜索')
        self.search_button.clicked.connect(self.start_search)
        control_layout.addWidget(self.search_button)
        
        main_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)
        
        # 结果显示区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        scroll.setWidget(self.results_widget)
        main_layout.addWidget(scroll)
        
    def show_history_menu(self, pos):
        """显示历史记录菜单"""
        menu = QMenu(self)
        
        if not self.processor.history:
            no_history = menu.addAction("无历史记录")
            no_history.setEnabled(False)
        else:
            for item in self.processor.history:
                action = menu.addAction(item['directory'])
                action.triggered.connect(lambda checked, d=item['directory']: self.load_history_directory(d))
                
        menu.exec_(self.dir_button.mapToGlobal(pos))
        
    def load_history_directory(self, directory):
        """加载历史记录中的目录"""
        if os.path.exists(directory):
            self.status_label.setText("正在索引文件...")
            self.progress_bar.setVisible(True)
            self.dir_button.setEnabled(False)
            self.search_button.setEnabled(False)
            
            self.index_worker = IndexWorker(self.processor, directory)
            self.index_worker.finished.connect(self.on_index_finished)
            self.index_worker.progress.connect(self.update_progress)
            self.index_worker.start()
            self.update_title()  # 更新标题
        else:
            self.status_label.setText("目录不存在")
        
    def select_directory(self):
        """选择要索引的目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择PDF文件目录")
        if directory:
            self.status_label.setText("正在索引文件...")
            self.progress_bar.setVisible(True)
            self.dir_button.setEnabled(False)
            self.search_button.setEnabled(False)
            
            self.index_worker = IndexWorker(self.processor, directory)
            self.index_worker.finished.connect(self.on_index_finished)
            self.index_worker.progress.connect(self.update_progress)
            self.index_worker.start()
            self.update_title()  # 更新标题
            
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(int(value))
            
    def on_index_finished(self):
        """索引完成回调"""
        self.dir_button.setEnabled(True)
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("索引完成，可以开始搜索")
        
    def start_search(self):
        """开始搜索"""
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.status_label.setText("正在搜索...")
        self.search_button.setEnabled(False)
        
        # 清除旧的搜索结果
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # 开始搜索
        self.search_worker = SearchWorker(self.processor, query)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()
        
    def on_search_finished(self, results):
        """搜索完成回调"""
        self.search_button.setEnabled(True)
        
        if not results:
            self.status_label.setText("未找到匹配结果")
            return
            
        self.status_label.setText(f"找到 {len(results)} 个匹配文件")
        
        # 显示结果
        for file_path, page_numbers in results.items():
            result_widget = ResultWidget(file_path, page_numbers)
            self.results_layout.addWidget(result_widget)
            
        # 添加弹性空间
        self.results_layout.addStretch()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 