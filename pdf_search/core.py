import os
import fitz  # PyMuPDF
import logging
import json
import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """搜索结果数据类"""
    file_path: str
    page_numbers: List[int]

class PDFProcessor:
    def __init__(self, index_dir: str = "pdf_index", history_file: str = "search_history.json"):
        """初始化PDF处理器
        
        Args:
            index_dir: 索引文件存储目录
            history_file: 历史记录文件路径
        """
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        self.history_file = Path(history_file)
        self.current_directory = None  # 添加当前目录属性
        
        # 定义搜索索引模式
        self.schema = Schema(
            path=ID(stored=True, unique=True),  # 添加unique=True确保路径唯一
            content=TEXT(stored=True),
            page_num=STORED
        )
        
        # 加载历史记录
        self.history = self._load_history()
        
        # 创建或打开索引
        if not os.listdir(self.index_dir):
            self.ix = create_in(self.index_dir, self.schema)
        else:
            self.ix = open_dir(self.index_dir)

    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self):
        """保存历史记录"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def add_to_history(self, directory: str):
        """添加目录到历史记录"""
        # 移除已存在的相同记录
        self.history = [h for h in self.history if h['directory'] != directory]
        
        # 添加新记录
        self.history.insert(0, {
            'directory': directory,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # 保持最多3条记录
        self.history = self.history[:3]
        
        # 保存历史记录
        self._save_history()

    def process_pdf(self, pdf_path: str) -> List[tuple]:
        """处理单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            List[Tuple[页码, 文本内容]]
        """
        try:
            doc = fitz.open(pdf_path)
            results = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                results.append((page_num + 1, text))
                
            doc.close()
            return results
            
        except Exception as e:
            logger.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")
            return []

    def index_directory(self, directory: str, progress_callback=None):
        """索引指定目录下的所有PDF文件
        
        Args:
            directory: 要索引的目录路径
            progress_callback: 进度回调函数
        """
        self.current_directory = directory  # 更新当前目录
        pdf_files = []
        
        # 递归搜索所有子文件夹中的PDF文件
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))

        if not pdf_files:
            return

        # 重新创建索引目录
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(exist_ok=True)
        self.ix = create_in(self.index_dir, self.schema)
        
        # 创建新的索引
        writer = self.ix.writer()
        total_files = len(pdf_files)
        
        with ProcessPoolExecutor() as executor:
            futures = []
            for pdf_path in pdf_files:
                future = executor.submit(self.process_pdf, pdf_path)
                futures.append((pdf_path, future))
                
            for i, (pdf_path, future) in enumerate(futures):
                try:
                    results = future.result()
                    # 使用集合去重页码
                    page_contents = {}
                    for page_num, content in results:
                        if page_num not in page_contents:
                            page_contents[page_num] = content
                            writer.add_document(
                                path=pdf_path,
                                content=content,
                                page_num=page_num
                            )
                    if progress_callback:
                        progress = (i + 1) / total_files * 100
                        progress_callback(progress)
                except Exception as e:
                    logger.error(f"索引文件 {pdf_path} 时出错: {str(e)}")
                    
        writer.commit()
        self.add_to_history(directory)

    def search(self, query: str) -> Dict[str, List[int]]:
        """搜索PDF内容
        
        Args:
            query: 搜索关键词
            
        Returns:
            Dict[文件路径, 页码列表]
        """
        results = {}
        
        with self.ix.searcher() as searcher:
            query_parser = QueryParser("content", self.ix.schema)
            q = query_parser.parse(query)
            search_results = searcher.search(q, limit=None)
            
            for hit in search_results:
                file_path = hit['path']
                page_num = hit['page_num']
                
                if file_path not in results:
                    results[file_path] = []
                if page_num not in results[file_path]:  # 确保页码不重复
                    results[file_path].append(page_num)
                
        # 对每个文件的页码进行排序
        for file_path in results:
            results[file_path].sort()
                
        return results

    def get_current_directory(self) -> Optional[str]:
        """获取当前索引的目录"""
        return self.current_directory 