import React, { useMemo, useState } from "react";
import "./CausalExplorer.css";
import { nodes, outcomeExplanations, policyPathGroups } from "./causalData";

const STRENGTH_WIDTH = {
  weak: 0.55,
  medium: 0.85,
  strong: 1.15,
};

const STRENGTH_OPACITY = {
  weak: 0.52,
  medium: 0.68,
  strong: 0.84,
};

const EFFECT_COLOR = {
  beneficial: "#3b9a6d",
  harmful: "#c96a5a",
};

const NODE_ASSET = {
  forest: "forest",
  levee: "levee",
  paddyDam: "paddy",
  relocation: "relocation",
  preparedness: "preparedness",
  agriRnd: "research",
  floodRisk: "flood",
  foodProduction: "crop",
  ecosystem: "ecosystem",
  residentBurden: "burden",
};

const NODE_ANCHORS = {
  forest: { out: { x: 4.4, y: 0.4 }, in: { x: -3.6, y: 1.8 } },
  levee: { out: { x: 4.8, y: 0.8 }, in: { x: -4.2, y: 1.2 } },
  paddyDam: { out: { x: 4.2, y: 1.6 }, in: { x: -4.0, y: 0.8 } },
  relocation: { out: { x: 4.8, y: 1.0 }, in: { x: -4.2, y: 0.6 } },
  preparedness: { out: { x: 4.0, y: -1.0 }, in: { x: -3.8, y: -0.4 } },
  agriRnd: { out: { x: 4.4, y: -1.2 }, in: { x: -4.0, y: -0.8 } },
  floodRisk: { in: { x: -6.8, y: 1.2 }, out: { x: 5.6, y: 0 } },
  foodProduction: { in: { x: -6.4, y: 0.2 }, out: { x: 5.6, y: 0 } },
  ecosystem: { in: { x: -6.2, y: -1.0 }, out: { x: 5.4, y: 0 } },
  residentBurden: { in: { x: -6.4, y: -1.2 }, out: { x: 5.6, y: 0 } },
  forestWater: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  waterRetention: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  floodDefense: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  heatTolerance: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  residentResilience: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  riskExposure: { in: { x: -1.2, y: 0 }, out: { x: 1.2, y: 0 } },
  policyCost: { in: { x: -1.2, y: -0.3 }, out: { x: 1.2, y: -0.3 } },
};

const EDGE_ANCHOR_OVERRIDES = {
  [edgeKey("forest", "forestWater")]: {
    from: { x: 5.4, y: -1.8 },
    to: { x: -1.0, y: 0.3 },
  },
  [edgeKey("forestWater", "waterRetention")]: {
    from: { x: 1.0, y: 0.5 },
    to: { x: -1.1, y: -0.5 },
  },
  [edgeKey("waterRetention", "floodRisk")]: {
    from: { x: 1.2, y: -0.4 },
    to: { x: -6.4, y: 1.3 },
  },
  [edgeKey("forestWater", "ecosystem")]: {
    from: { x: 1.1, y: 0.8 },
    to: { x: -6.2, y: -1.2 },
  },
  [edgeKey("forest", "policyCost")]: {
    from: { x: 5.2, y: 4.0 },
    to: { x: -1.2, y: -0.4 },
  },
  [edgeKey("policyCost", "residentBurden")]: {
    from: { x: 1.2, y: 0.1 },
    to: { x: -6.2, y: -1.4 },
  },
  [edgeKey("levee", "floodDefense")]: {
    from: { x: 5.2, y: 0.8 },
    to: { x: -1.3, y: -0.2 },
  },
  [edgeKey("relocation", "riskExposure")]: {
    from: { x: 5.4, y: 1.2 },
    to: { x: -1.2, y: 0.1 },
  },
  [edgeKey("preparedness", "residentResilience")]: {
    from: { x: 4.4, y: -2.0 },
    to: { x: 1.0, y: 0.1 },
  },
  [edgeKey("agriRnd", "heatTolerance")]: {
    from: { x: 5.0, y: -1.6 },
    to: { x: -1.2, y: 0 },
  },
};

function edgeKey(from, to) {
  return `${from}__${to}`;
}

function buildDerivedEdges(groups) {
  const edgeMap = new Map();
  const groupEdges = {};

  groups.forEach((group) => {
    groupEdges[group.id] = new Set();
    group.paths.forEach((path) => {
      const chain = path.chain || [];
      for (let i = 0; i < chain.length - 1; i += 1) {
        const from = chain[i];
        const to = chain[i + 1];
        const key = edgeKey(from, to);
        groupEdges[group.id].add(key);

        if (!edgeMap.has(key)) {
          edgeMap.set(key, {
            key,
            from,
            to,
            effect: path.effect,
            strength: path.strength,
            pathGroupIds: new Set([group.id]),
          });
        } else {
          const existing = edgeMap.get(key);
          existing.pathGroupIds.add(group.id);
          if (STRENGTH_WIDTH[path.strength] > STRENGTH_WIDTH[existing.strength]) {
            existing.strength = path.strength;
          }
          if (existing.effect !== path.effect) {
            existing.effect = "harmful";
          }
        }
      }
    });
  });

  return {
    edges: Array.from(edgeMap.values()).map((edge) => ({
      ...edge,
      pathGroupIds: Array.from(edge.pathGroupIds),
    })),
    groupEdges,
  };
}

function buildNodeLookup(nodeList) {
  return nodeList.reduce((acc, node) => {
    acc[node.id] = node;
    return acc;
  }, {});
}

function getOutcomeExplanation(targetId) {
  return outcomeExplanations.find((item) => item.target === targetId) || null;
}

function getPolicyGroup(sourceId) {
  return policyPathGroups.find((group) => group.source === sourceId) || null;
}

function getAnchorRadius(node) {
  if (node.type === "mechanism") return 1.8;
  if (node.type === "outcome") return 7.4;
  return 7.2;
}

function pointNearBoundary(fromNode, toNode, radius, role, edge) {
  const override = edge ? EDGE_ANCHOR_OVERRIDES[edge.key]?.[role] : null;
  const semanticOffset = override || NODE_ANCHORS[fromNode.id]?.[role];

  if (semanticOffset) {
    return {
      x: fromNode.x + semanticOffset.x,
      y: fromNode.y + semanticOffset.y,
    };
  }

  const dx = toNode.x - fromNode.x;
  const dy = toNode.y - fromNode.y;
  const distance = Math.sqrt(dx * dx + dy * dy) || 1;
  return {
    x: fromNode.x + (dx / distance) * radius,
    y: fromNode.y + (dy / distance) * radius,
  };
}

function toBezierPath(fromNode, toNode, edge) {
  const start = pointNearBoundary(fromNode, toNode, getAnchorRadius(fromNode), "out", edge);
  const end = pointNearBoundary(toNode, fromNode, getAnchorRadius(toNode), "in", edge);
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const curve = Math.max(8, Math.min(20, Math.abs(dx) * 0.42));
  const lift = Math.max(-5, Math.min(5, dy * 0.18));

  return `M ${start.x} ${start.y} C ${start.x + curve} ${start.y + lift}, ${end.x - curve} ${end.y - lift}, ${end.x} ${end.y}`;
}

function CausalExplorer({ embedded = false }) {
  const nodeMap = useMemo(() => buildNodeLookup(nodes), []);
  const { edges, groupEdges } = useMemo(() => buildDerivedEdges(policyPathGroups), []);

  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [lockedNodeId, setLockedNodeId] = useState(null);
  const [failedIconSet, setFailedIconSet] = useState({});

  const activeNodeId = lockedNodeId || hoveredNodeId;
  const activeNode = activeNodeId ? nodeMap[activeNodeId] : null;

  const activeState = useMemo(() => {
    if (!activeNode) {
      return {
        activeType: null,
        relatedNodeIds: new Set(),
        relatedEdgeKeys: new Set(),
        explanation: null,
        policyGroup: null,
      };
    }

    if (activeNode.type === "policy") {
      const group = getPolicyGroup(activeNode.id);
      const relatedNodeIds = new Set([activeNode.id]);
      const relatedEdgeKeys = new Set(group ? Array.from(groupEdges[group.id]) : []);

      if (group) {
        group.paths.forEach((path) => {
          path.chain.forEach((id) => relatedNodeIds.add(id));
        });
      }

      return {
        activeType: "policy",
        relatedNodeIds,
        relatedEdgeKeys,
        explanation: null,
        policyGroup: group,
      };
    }

    if (activeNode.type === "outcome") {
      const explanation = getOutcomeExplanation(activeNode.id);
      const relatedNodeIds = new Set([activeNode.id]);

      if (explanation) {
        explanation.relatedNodes.forEach((id) => relatedNodeIds.add(id));
      }

      const relatedEdgeKeys = new Set();
      edges.forEach((edge) => {
        if (
          (relatedNodeIds.has(edge.from) && relatedNodeIds.has(edge.to)) ||
          edge.to === activeNode.id
        ) {
          relatedEdgeKeys.add(edge.key);
        }
      });

      return {
        activeType: "outcome",
        relatedNodeIds,
        relatedEdgeKeys,
        explanation,
        policyGroup: null,
      };
    }

    return {
      activeType: "mechanism",
      relatedNodeIds: new Set([activeNode.id]),
      relatedEdgeKeys: new Set(),
      explanation: null,
      policyGroup: null,
    };
  }, [activeNode, edges, groupEdges]);

  function onBackgroundClick() {
    setLockedNodeId(null);
  }

  function onNodeMouseEnter(id) {
    if (!lockedNodeId) {
      setHoveredNodeId(id);
    }
  }

  function onNodeMouseLeave() {
    if (!lockedNodeId) {
      setHoveredNodeId(null);
    }
  }

  function onNodeClick(event, id) {
    event.stopPropagation();
    setLockedNodeId((prev) => (prev === id ? null : id));
  }

  function onIconError(nodeId) {
    setFailedIconSet((prev) => ({ ...prev, [nodeId]: true }));
  }

  function renderIcon(node) {
    const assetName = NODE_ASSET[node.id] || node.icon;
    const iconUrl =
      node.type !== "mechanism" && assetName
        ? `/causal-explorer-assets/${assetName}.png`
        : null;
    const isFailed = failedIconSet[node.id];

    if (node.type === "mechanism") {
      return <span className="ce-node__mechanism-dot" />;
    }

    if (!iconUrl || isFailed) {
      return <span>{node.fallbackIcon || node.id.slice(0, 2).toUpperCase()}</span>;
    }

    return (
      <img
        src={iconUrl}
        alt={node.labelEn}
        onError={() => onIconError(node.id)}
      />
    );
  }

  function nodeState(node) {
    if (!activeNode) {
      return node.type === "mechanism" ? "idle" : "default";
    }
    return activeState.relatedNodeIds.has(node.id) ? "visible" : "dimmed";
  }

  function edgeState(edge) {
    if (!activeNode) return "default";
    return activeState.relatedEdgeKeys.has(edge.key) ? "active" : "dimmed";
  }

  function panelContent() {
    if (!activeNode) {
      return {
        title: "メカニズム探索",
        summary:
          "政策や結果指標にカーソルを合わせると、関係する影響経路が表示されます。",
        note: lockedNodeId
          ? "背景をクリックすると固定表示を解除できます。"
          : "ノードをクリックするとハイライトを固定できます。",
        bullets: [],
      };
    }

    if (activeState.activeType === "policy" && activeState.policyGroup) {
      return {
        title: activeState.policyGroup.titleJa,
        summary: activeState.policyGroup.summaryJa,
        note: activeState.policyGroup.noteJa,
        bullets: activeState.policyGroup.paths.map((path) => path.summaryJa),
      };
    }

    if (activeState.activeType === "outcome" && activeState.explanation) {
      return {
        title: `${activeNode.labelJa} / ${activeNode.labelEn}`,
        summary: activeState.explanation.summaryJa,
        note: "関連する政策・メカニズム経路を強調表示しています。",
        bullets: [],
      };
    }

    return {
      title: `${activeNode.labelJa} / ${activeNode.labelEn}`,
      summary: "関連経路を表示しています。",
      note: "",
      bullets: [],
    };
  }

  const panel = panelContent();

  return (
    <div
      className={`causal-explorer ${embedded ? "causal-explorer--embedded" : ""}`}
      onClick={onBackgroundClick}
    >
      <div className="causal-explorer__title">
        <h2>Causal Explorer</h2>
        <p>政策と結果の因果経路を可視化</p>
      </div>

      <div className="causal-explorer__canvas">
        <svg className="causal-explorer__edges" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <marker id="arrow-beneficial" markerWidth="3.4" markerHeight="3.4" refX="3.2" refY="1.7" orient="auto">
              <path d="M0,0 L3.4,1.7 L0,3.4 z" fill={EFFECT_COLOR.beneficial} />
            </marker>
            <marker id="arrow-harmful" markerWidth="3.4" markerHeight="3.4" refX="3.2" refY="1.7" orient="auto">
              <path d="M0,0 L3.4,1.7 L0,3.4 z" fill={EFFECT_COLOR.harmful} />
            </marker>
          </defs>

          {edges.map((edge) => {
            const fromNode = nodeMap[edge.from];
            const toNode = nodeMap[edge.to];
            if (!fromNode || !toNode) return null;

            const state = edgeState(edge);
            return (
              <path
                key={edge.key}
                className={`ce-edge ce-edge--${edge.effect} ce-edge--${edge.strength} ${
                  state === "active" ? "is-active" : ""
                } ${state === "dimmed" ? "is-dimmed" : "is-default"}`}
                d={toBezierPath(fromNode, toNode, edge)}
                stroke={EFFECT_COLOR[edge.effect]}
                strokeWidth={STRENGTH_WIDTH[edge.strength]}
                strokeOpacity={STRENGTH_OPACITY[edge.strength]}
                markerEnd={`url(#arrow-${edge.effect})`}
              />
            );
          })}
        </svg>

        <div className="causal-explorer__nodes">
          {nodes.map((node) => {
            const state = nodeState(node);
            const isActive = activeNodeId === node.id;
            const isLocked = lockedNodeId === node.id;

            return (
              <button
                key={node.id}
                type="button"
                className={`ce-node ce-node--${node.type} ${isActive ? "is-active" : ""} ${
                  isLocked ? "is-locked" : ""
                } ${state === "dimmed" ? "is-dimmed" : ""} ${
                  node.type === "mechanism" && !activeNode ? "is-idle" : ""
                } ${node.type === "mechanism" && state === "visible" ? "is-visible" : ""}`}
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
                onMouseEnter={() => onNodeMouseEnter(node.id)}
                onMouseLeave={onNodeMouseLeave}
                onClick={(event) => onNodeClick(event, node.id)}
                aria-label={node.labelJa}
              >
                <span className="ce-node__anchor">
                  <span className="ce-node__icon">{renderIcon(node)}</span>
                </span>
                <span className="ce-node__label">
                  <span className="ce-node__ja">{node.labelJa}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="causal-explorer__panel">
        <h3>{panel.title}</h3>
        <p>{panel.summary}</p>
        {panel.note ? <p className="causal-explorer__panel-note">{panel.note}</p> : null}
        {panel.bullets.length > 0 ? (
          <ul>
            {panel.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

export default CausalExplorer;
