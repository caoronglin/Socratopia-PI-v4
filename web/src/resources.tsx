import { useEffect, useState } from 'react';
import { Alert, Button, Card, Divider, Empty, Flex, Input, Listy, Space, Tag, Typography, Upload } from 'antd';
import type { CourseRequest } from './practice';

type Chapter = { title: string; level: number; line: number };
type Book = { course: string; available: boolean; can_import: boolean;
  sha256?: string; bytes?: number; source?: string; chapters: Chapter[] };
const { Text, Paragraph } = Typography;

export default function ResourcesPanel({ course, request, onImported, onExplore, onStartPrep }: {
  course: string; request: CourseRequest; onImported: () => void;
  onExplore: (title: string) => void; onStartPrep: () => void;
}) {
  const [book, setBook] = useState<Book | null>(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let mounted = true;
    setContent(''); setError(''); setBook(null);
    void request<Book>('/courses/' + encodeURIComponent(course) + '/book')
      .then(value => { if (mounted) setBook(value); })
      .catch(err => { if (mounted) setError(err instanceof Error ? err.message : '读取教材失败'); });
    return () => { mounted = false; };
  }, [course, request]);
  const importBook = async () => {
    if (!content.trim()) return;
    setLoading(true); setError('');
    try {
      await request('/courses/' + encodeURIComponent(course) + '/book', 'POST', { content });
      const latest = await request<Book>('/courses/' + encodeURIComponent(course) + '/book');
      setBook(latest); setContent(''); onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : '教材导入失败');
    } finally { setLoading(false); }
  };
  return <Card className="control-card" title="教材与章节" extra={<Tag>本课程独立存储</Tag>}>
    {error && <Alert type="error" showIcon className="feedback" title={error} />}
    {!book ? <Text type="secondary">读取教材状态中…</Text> :
      book.available ? <>
        <Flex gap="small" wrap="wrap" align="center" justify="space-between">
          <Space wrap><Tag color="success">主教材已载入</Tag><Text type="secondary">{book.source}</Text></Space>
          <Button type="primary" onClick={onStartPrep}>下一步：章节备课</Button>
        </Flex>
        <Paragraph copyable={{ text: book.sha256 }} type="secondary">
          文件摘要 SHA-256：{book.sha256?.slice(0, 16)}… · {book.bytes?.toLocaleString()} 字节
        </Paragraph>
        <Divider />
        <Text strong>章节目录（点击章节立即检索对应教材证据）</Text>
        {book.chapters.length ? <Listy items={book.chapters} rowKey="line"
          itemRender={chapter => <Flex align="center" justify="space-between" wrap="wrap" gap="small">
            <Button type="link" onClick={() => onExplore(chapter.title)}>
              {chapter.level > 1 ? '　'.repeat(chapter.level - 1) : ''}{chapter.title}
            </Button>
            <Text type="secondary">第 {chapter.line} 行</Text>
          </Flex>} /> : <Empty description="教材中暂无 Markdown 标题；仍可使用正文进行证据检索" />}
      </> : <>
        <Alert type="warning" showIcon title="尚无主教材"
          description="可导入 Markdown/TXT 教材或粘贴正文；原有教材一律不可覆盖，导入不会自动解除正式开课 PREP 门禁。" />
        <div className="import-form">
          <Upload accept=".md,.markdown,.txt,text/plain,text/markdown"
            maxCount={1} showUploadList={false}
            beforeUpload={file => {
              if (file.size > 2000000) {
                setError('教材文件不能超过 2 MB'); return Upload.LIST_IGNORE;
              }
              void file.text().then(text => { setError(''); setContent(text); })
                .catch(() => setError('文件不是有效的文本教材'));
              return Upload.LIST_IGNORE;
            }}>
            <Button>选择本地 Markdown / TXT 文件</Button>
          </Upload>
          <Input.TextArea value={content} onChange={e => setContent(e.target.value)}
            rows={7} maxLength={2000000} placeholder="# 第一章&#10;教材正文（请确保有权使用和整理此内容）" />
          <Space wrap><Button type="primary" loading={loading} disabled={new TextEncoder().encode(content).length < 32}
            onClick={() => void importBook()}>确认导入（只创建，不覆盖）</Button>
            <Text type="secondary">导入后还需章节备课才能正式开课。</Text></Space>
        </div>
      </>}
    {book?.available && book.chapters.length === 0 && <Empty description="可使用下方证据检索" />}
  </Card>;
}
