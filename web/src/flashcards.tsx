import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Collapse, Empty, Flex, Form, Input, Select, Space, Statistic, Tag, Typography } from 'antd';

const { Text, Paragraph } = Typography;
type Request = <T,>(path: string, method?: string, body?: object) => Promise<T>;
type Preview = {
  id: string; front: string; concept_id: string | null; concept_label: string | null;
  exercise_id: string | null; status: 'needs_attention' | 'due' | 'new' | 'upcoming';
  due_at: string | null; recent_correct_streak: number; source_current: true;
};
type Deck = {
  course: string; status: 'needs_textbook' | 'needs_cards' | 'ready';
  total_cards: number; active_cards: number; stale_cards_excluded: number;
  review_due: number; new_cards: number; linked_weaknesses: number;
  suggested_minutes: number; items: Preview[]; upcoming: Preview[];
  mastery_updated: false; note: string;
};
type Revealed = {
  id: string; back: string; source_quote: string; source_sha256: string;
  reveal_token: string; fact_verified: false; mastery_updated: false;
};
type Review = { card_id: string; next_review_at: string; replayed: boolean; mastery_updated: false };
type Graph = { nodes: { id: string; label: string }[] };
type Quiz = { questions: { id: string; stem: string; source_current: boolean }[] };
type Props = { course: string; request: Request };
const LABEL: Record<Preview['status'], string> = {
  needs_attention: '错题关联', due: '到期复习', new: '首次学习', upcoming: '未到期',
};

export default function FlashcardsPanel({ course, request }: Props) {
  const prefix = '/courses/' + encodeURIComponent(course);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [concepts, setConcepts] = useState<Graph['nodes']>([]);
  const [quizzes, setQuizzes] = useState<Quiz['questions']>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Revealed | null>(null);
  const [requestId, setRequestId] = useState('');
  const [completed, setCompleted] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [front, setFront] = useState('');
  const [back, setBack] = useState('');
  const [quote, setQuote] = useState('');
  const [conceptId, setConceptId] = useState<string | undefined>();
  const [exerciseId, setExerciseId] = useState<string | undefined>();

  const reload = useCallback(async () => {
    setDeck(await request<Deck>(prefix + '/flashcards'));
  }, [prefix, request]);

  useEffect(() => {
    let alive = true;
    setDeck(null); setCurrentId(null); setRevealed(null); setCompleted([]);
    setError(''); setFeedback('');
    void Promise.all([
      request<Deck>(prefix + '/flashcards'),
      request<Graph>(prefix + '/graph').catch(() => ({ nodes: [] })),
      request<Quiz>(prefix + '/exercises').catch(() => ({ questions: [] })),
    ]).then(([cards, graph, exercises]) => {
      if (!alive) return;
      setDeck(cards); setConcepts(graph.nodes); setQuizzes(exercises.questions);
    }).catch(err => {
      if (alive) setError(err instanceof Error ? err.message : '闪卡读取失败');
    });
    return () => { alive = false; };
  }, [prefix, request]);

  const queue = useMemo(() => (deck?.items || []).filter(c => !completed.includes(c.id)),
    [deck, completed]);
  const active = queue.find(card => card.id === currentId) || queue[0];
  const shown = revealed && active?.id === revealed.id ? revealed : null;

  const select = (id: string) => {
    setCurrentId(id); setRevealed(null); setRequestId(''); setError(''); setFeedback('');
  };
  const uncover = async () => {
    if (!active || busy || shown) return;
    setBusy(true); setError(''); setFeedback('');
    try {
      setRevealed(await request<Revealed>(
        prefix + '/flashcards/' + active.id + '/reveal', 'POST', {},
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法翻开卡片');
    } finally { setBusy(false); }
  };
  const rate = async (rating: 'again' | 'hard' | 'good' | 'easy') => {
    if (!active || !shown || busy) return;
    const id = requestId || crypto.randomUUID().replaceAll('-', '');
    setRequestId(id); setBusy(true); setError('');
    try {
      const result = await request<Review>(
        prefix + '/flashcards/' + active.id + '/review', 'POST',
        { rating, reveal_token: shown.reveal_token, request_id: id },
      );
      setCompleted(previous => [...previous, active.id]);
      setCurrentId(null); setRevealed(null); setRequestId('');
      setFeedback('本次自评已保存。下次建议复习：' +
        new Date(result.next_review_at).toLocaleString('zh-CN'));
      try { await reload(); }
      catch { setError('记录已保存，列表刷新失败；可点击重新读取。'); }
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法保存复习记录');
    } finally { setBusy(false); }
  };
  const createCard = async () => {
    if (busy) return;
    setBusy(true); setError(''); setFeedback('');
    try {
      await request(prefix + '/flashcards', 'POST', {
        front: front.trim(), back: back.trim(), source_quote: quote.trim(),
        concept_id: conceptId ?? null, exercise_id: exerciseId ?? null,
      });
      setFront(''); setBack(''); setQuote('');
      setConceptId(undefined); setExerciseId(undefined);
      setCompleted([]); setCurrentId(null); setRevealed(null);
      await reload();
      setFeedback('闪卡已保存，并绑定当前教材版本。');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建闪卡失败');
    } finally { setBusy(false); }
  };

  return <div className="flashcard-workspace">
    <Card title="记忆闪卡 · 主动回忆" extra={<Tag>本地复习 · 无模型调用</Tag>}>
      <Paragraph type="secondary">
        先凭记忆回答，再翻卡核对教材，最后按实际回忆情况自评。
        系统只建议下次复习，不自动认定掌握，也不替代正式课堂。
      </Paragraph>
      {error && <Alert type="error" showIcon className="feedback" title={error} />}
      {feedback && <Alert type="success" showIcon className="feedback" title={feedback} />}
      {deck && <Flex wrap="wrap" gap="large" className="flashcard-stats">
        <Statistic title="建议复习" value={deck.review_due} suffix="张" />
        <Statistic title="首次学习" value={deck.new_cards} suffix="张" />
        <Statistic title="关联错题" value={deck.linked_weaknesses} suffix="张" />
        <Statistic title="本次建议" value={deck.suggested_minutes} suffix="分钟" />
      </Flex>}
      {Boolean(deck?.stale_cards_excluded) && <Alert type="warning" showIcon className="feedback"
        title={String(deck?.stale_cards_excluded) + ' 张旧教材闪卡已暂停复习'} />}
      {!deck ? <Card loading bordered={false} /> :
        deck.status === 'needs_textbook' ?
          <Empty description="请先导入本课程教材，再创建带有原文证据的闪卡" /> :
        deck.status === 'needs_cards' ?
          <Empty description="本课程暂无可用闪卡，可以在下方创建第一张" /> :
        active ? <>
          <Flex gap="small" wrap="wrap" className="flashcard-queue" aria-label="本次闪卡复习队列">
            {queue.map((card, index) => <Button key={card.id} size="small"
              type={active.id === card.id ? 'primary' : 'default'} disabled={busy}
              onClick={() => select(card.id)}>
              {index + 1} · {LABEL[card.status]}
            </Button>)}
          </Flex>
          <section className="flashcard-face" aria-label="当前记忆闪卡">
            <Flex wrap="wrap" gap="small" justify="center">
              <Tag color={active.status === 'needs_attention' ? 'warning' : 'default'}>
                {LABEL[active.status]}
              </Tag>
              {active.concept_label && <Tag>{active.concept_label}</Tag>}
              {active.exercise_id && <Tag>关联课堂练习</Tag>}
            </Flex>
            <Typography.Title level={4} className="flashcard-question">{active.front}</Typography.Title>
            {!shown ? <>
              <Text type="secondary">尝试先说出或写出答案，再翻开卡片。</Text>
              <Button size="large" type="primary" disabled={busy} loading={busy}
                onClick={() => void uncover()}>显示答案</Button>
            </> : <>
              <div className="flashcard-back" aria-live="polite">
                <Text strong>参考答案</Text>
                <Paragraph>{shown.back}</Paragraph>
                <Text type="secondary">教材原文（逐字核对）：</Text>
                <Paragraph className="flashcard-source">{shown.source_quote}</Paragraph>
                <Text type="secondary">教材版本：{shown.source_sha256.slice(0, 16)}…</Text>
              </div>
              <Text type="secondary">你刚才独立回忆得如何？这是自评，不是自动评分。</Text>
              <Flex justify="center" wrap="wrap" gap="small">
                <Button disabled={busy} onClick={() => void rate('again')}>未想起 · 10 分钟</Button>
                <Button disabled={busy} onClick={() => void rate('hard')}>困难 · 1 天</Button>
                <Button disabled={busy} type="primary" onClick={() => void rate('good')}>记得 · 间隔复习</Button>
                <Button disabled={busy} onClick={() => void rate('easy')}>很熟悉 · 延长间隔</Button>
              </Flex>
            </>}
          </section>
        </> : <Empty description="本次推荐闪卡已复习完成，可以休息或下次继续。" />}
      <Flex style={{ marginTop: 12 }} justify="end">
        <Button size="small" onClick={() => {
          setCompleted([]); setRevealed(null);
          void reload().catch(err => setError(err instanceof Error ? err.message : '刷新失败'));
        }}>重新读取复习队列</Button>
      </Flex>
      <Paragraph type="secondary" className="section-note">
        间隔时间仅为启发式建议，练习质量比打卡数量更重要。
      </Paragraph>
    </Card>
    <Collapse items={[{
      key: 'create', label: '新建教材闪卡（人工核对答案）',
      children: <Form layout="vertical" onFinish={() => void createCard()}>
        <Alert type="info" showIcon className="feedback"
          title="闪卡背面不会由模型自动确认为正确"
          description="请先核对教材，提供逐字原文；可关联章节节点或课堂练习。教材修订后旧卡暂停复习。" />
        <Form.Item label="正面 · 主动回忆问题">
          <Input.TextArea value={front} maxLength={240} showCount rows={2}
            onChange={e => setFront(e.target.value)} placeholder="例如：减数分裂为什么使染色体数目减半？" />
        </Form.Item>
        <Form.Item label="背面 · 核实后的参考答案">
          <Input.TextArea value={back} maxLength={800} showCount rows={3}
            onChange={e => setBack(e.target.value)} placeholder="简洁解释关键机制" />
        </Form.Item>
        <Form.Item label="教材原文（8–500 字，逐字匹配）">
          <Input.TextArea value={quote} maxLength={500} showCount rows={2}
            onChange={e => setQuote(e.target.value)} placeholder="从当前教材复制一段可核对的原文" />
        </Form.Item>
        <Form.Item label="关联章节 / 图谱节点（可选）">
          <Select allowClear showSearch optionFilterProp="label"
            placeholder="选择当前教材中的章节标题" value={conceptId} onChange={setConceptId}
            options={concepts.map(node => ({ value: node.id, label: node.label }))} />
        </Form.Item>
        <Form.Item label="关联练习（可选 · 错题优先复习）">
          <Select allowClear showSearch optionFilterProp="label"
            placeholder="关联一题已审核的练习" value={exerciseId} onChange={setExerciseId}
            options={quizzes.filter(q => q.source_current).map(q => ({ value: q.id, label: q.stem }))} />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={busy}
          disabled={front.trim().length < 3 || !back.trim() || quote.trim().length < 8}>
          保存闪卡
        </Button>
      </Form>,
    }]} />
  </div>;
}
