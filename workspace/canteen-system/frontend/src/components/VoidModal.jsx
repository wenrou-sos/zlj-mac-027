import React, { useEffect, useState } from 'react'
import { Input, Modal, message } from 'antd'

/** 作废/停用原因弹窗：原因必填留档，确认后回调 onOk(reason) */
export default function VoidModal({ open, title, label = '作废原因', onOk, onCancel }) {
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (open) setReason('')
  }, [open])

  const ok = () => {
    if (!reason.trim()) {
      message.warning(`请填写${label}`)
      return
    }
    onOk(reason.trim())
  }

  return (
    <Modal
      title={title}
      open={open}
      onOk={ok}
      onCancel={onCancel}
      okText="确认作废"
      okButtonProps={{ danger: true }}
      cancelText="取消"
      destroyOnClose
    >
      <p style={{ color: '#666' }}>
        作废后原记录保留在「已作废」视图中可查可恢复，不会物理删除。
      </p>
      <Input.TextArea
        rows={2}
        placeholder={`请填写${label}（必填，留档备查）`}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
    </Modal>
  )
}
