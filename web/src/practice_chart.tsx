import { useEffect, useRef } from 'react';
import { Empty } from 'antd';
import { Chart } from '@antv/g2';

type Datum = { day: string; correct: number; incorrect: number };
export default function PracticeChart({ data }: { data: Datum[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element || !data.length) return;
    const chart = new Chart({ container: element, autoFit: true, height: 210 });
    chart.options({
      type: 'interval',
      data: data.flatMap(item => [
        { day: item.day, count: item.correct, outcome: '正确' },
        { day: item.day, count: item.incorrect, outcome: '待加强' },
      ]),
      transform: [{ type: 'stackY' }],
      encode: { x: 'day', y: 'count', color: 'outcome' },
      axis: { y: { title: '次数' }, x: { title: false } },
    });
    void chart.render();
    return () => { chart.destroy(); };
  }, [data]);
  if (!data.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="提交练习后显示 AntV 趋势图" />;
  return <div ref={ref} className="practice-chart" role="img" aria-label="AntV 练习答题正确和错误次数趋势图" />;
}
