<template>
  <div class="help-center">
    <div class="help-header">
      <h1>帮助中心</h1>
      <p>快速查看智能会议助手的核心功能和常见问题。</p>
    </div>

    <el-row :gutter="16" class="help-grid">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="help-card">
          <template #header>
            <div class="card-title">快速开始</div>
          </template>
          <ol>
            <li>进入会议管理，点击新建会议。</li>
            <li>上传音频或开始实时转录。</li>
            <li>在会议详情查看摘要、行动项和决策点。</li>
            <li>将行动项导入任务主页进行追踪。</li>
          </ol>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="help-card">
          <template #header>
            <div class="card-title">功能说明</div>
          </template>
          <ul>
            <li>会议管理：创建、查看、删除会议记录。</li>
            <li>会议详情：查看转录、摘要、行动项并编辑。</li>
            <li>任务主页：集中管理任务优先级、负责人和截止日期。</li>
            <li>站内提醒：关注逾期和即将到期任务。</li>
          </ul>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="help-card">
          <template #header>
            <div class="card-title">常见问题</div>
          </template>
          <ul>
            <li>看不到摘要：先确认会议已完成转录并刷新摘要。</li>
            <li>导入任务失败：请先选择关联会议并填写任务标题。</li>
            <li>权限异常：重新登录后重试相关操作。</li>
          </ul>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="help-card">
          <template #header>
            <div class="card-title">建议流程</div>
          </template>
          <ol>
            <li>先在会议详情完善摘要与行动项责任人。</li>
            <li>批量导入行动项到任务系统。</li>
            <li>每日在任务主页处理提醒列表。</li>
            <li>会议复盘时导出摘要留档。</li>
          </ol>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
</script>

<style scoped lang="scss">
.help-center {
  padding: 12px 0;

  .help-header {
    margin-bottom: 18px;
    border-radius: 16px;
    padding: 18px 20px;
    background: linear-gradient(120deg, rgba(102, 126, 234, 0.16), rgba(79, 172, 254, 0.14));
    border: 1px solid rgba(136, 153, 240, 0.25);

    h1 {
      margin: 0;
      font-size: 28px;
      background: var(--grad-primary);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }

    p {
      margin: 8px 0 0;
      color: #4f5f86;
    }
  }

  .help-grid {
    row-gap: 16px;
  }

  .help-card {
    height: 100%;

    .card-title {
      font-weight: 700;
      color: #34476b;
    }

    ul,
    ol {
      margin: 0;
      padding-left: 18px;
      color: #43506b;
      line-height: 1.8;
    }
  }
}
</style>
