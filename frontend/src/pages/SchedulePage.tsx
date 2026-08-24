import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function SchedulePage() {
  const { data = [] } = useQuery({ queryKey: ["schedule"], queryFn: api.schedules });
  return (
    <div className="page">
      <section className="page-header">
        <div><p className="eyebrow">Schedule Center</p><h1>开发排期</h1><p>项目、品牌、状态与风险视图。</p></div>
      </section>
      <section className="filter-bar"><button>项目</button><button>品牌</button><button>状态</button><button>日期范围</button></section>
      <section className="panel">
        <div className="section-title"><h2>Timeline / Gantt</h2><span>{data.length} 项</span></div>
        {data.length ? data.map((item) => <article className="project-row" key={item.key}><strong>{item.name}</strong><span>{item.status} / {item.milestone} / Risk {item.risk}</span></article>) : <p className="empty">暂无排期数据</p>}
      </section>
    </div>
  );
}
