- # Paper2GNNLab-Agent：面向图神经网络论文阅读与实验复现的科研 Agent

  ## 项目定位

  Paper2GNNLab-Agent 是一个面向图神经网络、异构图学习与图鲁棒性研究场景的科研辅助 Agent。项目并不只提供通用论文问答能力，而是围绕 GNN 论文复现流程，设计了 GNN-specific 结构化抽取 schema、论文对比维度、复现计划生成和实验框架代码生成能力。

  系统支持单篇 / 多篇论文上传解析，自动生成结构化论文卡片，过滤参考文献、页眉页脚、无关声明等低价值文本，并保留页码、章节和 chunk_id 等引用信息。用户可以围绕论文内容进行带 citations 的问答，也可以对多篇论文在任务类型、图类型、数据集、攻击设置、模型模块、评价指标和复现难点等维度进行横向对比。

  在实验复现方面，系统会将论文内容抽取为 method_spec.yaml，包含 task_type、graph_type、datasets、model_modules、losses、attacks、metrics、baselines 和 missing_details 等字段。随后 Agent 根据该结构化 spec 和预定义异构图实验框架模板，生成实验项目骨架，包括模型文件、配置文件、运行脚本、攻击配置、复现 README 和 TODO 清单。当前阶段代码生成以可审查的项目骨架和模块草稿为主，保留人工确认与补充环节，避免直接生成不可控的完整复现代码。

  ## 核心功能

  1. 论文上传与复用
     系统对上传论文计算 file_hash。若论文已解析，则直接复用已有 paper_id、chunks、embeddings、paper_card、citations 和 method_spec；若论文未解析，则执行 PDF 解析、文本清洗、chunk 切分、向量化和结构化抽取。
  2. 结构化论文卡片生成
     针对 GNN 论文抽取研究问题、任务类型、图类型、数据集、模型模块、训练目标、攻击方式、防御策略、评价指标、baseline、主要结果和复现难点。
  3. 带引用的论文问答
     支持围绕单篇或多篇论文进行问答，返回答案的同时给出对应 paper_id、section、page、chunk_id 和原文证据，提升答案可追溯性。
  4. 多论文横向对比
     支持从任务定义、图类型、数据集、攻击设置、指标、实验公平性和复现难度等维度对比多篇论文，辅助确定 baseline 和后续实验方案。
  5. 复现计划生成
     根据论文结构化信息生成复现 checklist，包括环境依赖、数据准备、模型模块、攻击方法、训练流程、评价指标、消融实验和论文中缺失的实现细节。
  6. 实验代码骨架生成
     根据 method_spec.yaml 和预定义 GNN 实验框架模板，生成可审查的实验项目文件夹，包括 models、configs、scripts、attacks、README_reproduce.md 和 TODO.md，辅助从论文阅读过渡到实验实现。
  7. GraphRAG 联动
     系统可将已有 GraphRAG 项目作为底层证据检索工具，通过 API 调用其向量检索、图谱检索、Hybrid Evidence 和 citations 能力；本项目则聚焦 Agent Router、工具编排、复现计划和代码生成工作流。