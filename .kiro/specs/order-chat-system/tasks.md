# Implementation Plan: Order & Chat System

## Overview

在现有纺织面料平台基础上实现报价转订单流程和会话聊天系统。后端使用 Python/Flask，前端使用微信小程序。任务按增量方式组织：先修改数据模型，再实现后端 API，最后修改/新增前端页面。

## Tasks

- [x] 1. Update Order model and create Conversation/ChatMessage models
  - [x] 1.1 Add demand_id, quote_id, tracking_no fields to Order model in `server/models/order.py`
    - Add nullable ForeignKey columns: `demand_id` → demands.id, `quote_id` → quotes.id
    - Add `tracking_no = db.Column(db.String(100), nullable=True)`
    - Add relationships: `demand`, `quote`
    - Update `to_dict()` to include new fields
    - _Requirements: 1.2, 3.1, 4.3_

  - [x] 1.2 Create Conversation and ChatMessage models in `server/models/conversation.py`
    - Create `Conversation` model with fields: id, demand_id, buyer_id, supplier_id, last_message_at, last_message_preview, created_at
    - Add UniqueConstraint on (demand_id, buyer_id, supplier_id)
    - Create `ChatMessage` model with fields: id, conversation_id, sender_id, content, msg_type (text/system), is_read, created_at
    - Add `to_dict()` methods on both models
    - Add relationships to User and Demand
    - _Requirements: 6.1, 6.2, 7.1_

  - [ ]* 1.3 Write property tests for Order model changes
    - **Property 4: Order detail contains all required fields and timeline**
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [ ]* 1.4 Write property test for Conversation uniqueness
    - **Property 9: Conversation creation idempotence**
    - **Validates: Requirements 6.2**

- [ ] 2. Implement accept-quote API and order creation from quote
  - [x] 2.1 Add accept quote endpoint in `server/routes/demand.py`
    - `PUT /api/demands/<demand_id>/quotes/<quote_id>/accept`
    - Verify buyer owns the demand, demand is "open", quote belongs to demand
    - Set accepted quote to "accepted", other quotes to "rejected", demand to "closed"
    - Create Order with demand_id, quote_id, buyer_id, supplier_id, total_amount = quote.price * demand.quantity
    - Create or get Conversation for (demand, buyer, supplier)
    - Add initial system ChatMessage with quote summary
    - Send notification to supplier
    - Return created order and conversation_id
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.3_

  - [ ]* 2.2 Write property test for accept quote flow
    - **Property 1: Accept quote produces correct order and state changes**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]* 2.3 Write property test for quote submission creating conversation
    - **Property 8: Quote submission creates conversation**
    - **Validates: Requirements 6.1**

  - [ ]* 2.4 Write property test for new conversation system message
    - **Property 10: New conversation has system message**
    - **Validates: Requirements 6.3**

- [x] 3. Update order routes for role-based access and enhanced detail
  - [x] 3.1 Modify `list_orders` in `server/routes/order.py` to support admin role and enhanced response
    - Admin role sees all orders (no filter)
    - Add optional `status` query parameter for filtering
    - Include demand_title, quote_price, counterparty company_name in each order item via joins
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 9.3_

  - [x] 3.2 Modify `get_order_detail` in `server/routes/order.py` to support admin and include demand/quote info
    - Allow admin to view any order
    - Include demand info (title, quantity) and quote info (price, delivery_days) in response
    - Include tracking_no in response
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.3 Modify `update_order_status` in `server/routes/order.py` to accept tracking_no and allow buyer to complete
    - Accept `tracking_no` in request body when transitioning to "shipped"
    - Allow buyer to transition from "received" to "completed"
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

  - [ ]* 3.4 Write property tests for role-based order filtering
    - **Property 2: Role-based order list filtering**
    - **Validates: Requirements 2.1, 2.2, 2.3, 9.3**

  - [ ]* 3.5 Write property tests for status transitions
    - **Property 5: Valid sequential status transitions succeed**
    - **Property 7: Invalid status transitions are rejected**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5, 5.1, 5.2, 5.4**

  - [ ]* 3.6 Write property test for status change notifications
    - **Property 6: Status change triggers notification**
    - **Validates: Requirements 4.4, 5.3**

- [x] 4. Checkpoint - Backend order flow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement conversation and chat message routes
  - [x] 5.1 Create `server/routes/conversation.py` with conversation list endpoint
    - `GET /api/conversations` with pagination
    - Buyer/Supplier: filter by buyer_id or supplier_id
    - Admin: return all conversations
    - Include counterparty company_name, demand_title, last_message_preview, last_message_at, unread_count per conversation
    - Sort by last_message_at descending
    - _Requirements: 8.1, 8.2, 9.1_

  - [x] 5.2 Add chat message endpoints in `server/routes/conversation.py`
    - `GET /api/conversations/<conv_id>/messages` with pagination, chronological order
    - Auto-mark other party's messages as read on GET
    - `POST /api/conversations/<conv_id>/messages` for participants only (not admin)
    - Update conversation last_message_at and last_message_preview on POST
    - Validate non-empty content
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 9.2_

  - [x] 5.3 Add unread conversation count endpoint
    - `GET /api/conversations/unread-count`
    - Count ChatMessages where user is participant, sender is other party, is_read is False
    - _Requirements: 8.4_

  - [x] 5.4 Register conversation blueprint in `server/app.py`
    - Import and register `conversation_bp` with url_prefix `/api/conversations`
    - _Requirements: 8.1_

  - [ ]* 5.5 Write property tests for conversation list filtering and sorting
    - **Property 14: Conversation list is role-filtered and sorted**
    - **Validates: Requirements 8.1, 9.1**

  - [ ]* 5.6 Write property tests for message storage and conversation update
    - **Property 11: Sent message stored and conversation metadata updated**
    - **Property 12: Messages returned in chronological order**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [ ]* 5.7 Write property test for read marking
    - **Property 13: Opening conversation marks messages as read**
    - **Validates: Requirements 7.4**

  - [ ]* 5.8 Write property test for unread count
    - **Property 16: Unread conversation count accuracy**
    - **Validates: Requirements 8.4**

- [x] 6. Checkpoint - Backend chat system
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update demand detail frontend to support accepting quotes
  - [x] 7.1 Modify `miniprogram/pages/demand/detail/detail.js` to add accept quote functionality
    - Add `acceptQuote(quoteId)` method calling `PUT /api/demands/:id/quotes/:qid/accept`
    - Show confirmation dialog before accepting
    - On success, navigate to order detail page
    - Refresh quote list after acceptance
    - _Requirements: 1.1, 1.2_

  - [x] 7.2 Modify `miniprogram/pages/demand/detail/detail.wxml` to add accept button on each quote card
    - Add "接受报价" button on each quote item (only for buyer, only when demand is open)
    - Show accepted/rejected status tag on quotes when demand is closed
    - _Requirements: 1.1_

  - [x] 7.3 Update `miniprogram/pages/demand/detail/detail.wxss` for accept button styling
    - Style the accept button with macaron green color scheme
    - Style status tags for accepted/rejected quotes
    - _Requirements: 1.1_

- [x] 8. Update order list and detail frontend pages
  - [x] 8.1 Modify `miniprogram/pages/order/list/list.js` to show demand title and counterparty info
    - Update `_processOrderItem` to extract demand_title, counterparty name from response
    - Handle admin role showing all orders
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 8.2 Modify `miniprogram/pages/order/list/list.wxml` to display demand title and counterparty
    - Show demand title as secondary text on order card
    - Show counterparty company name
    - _Requirements: 2.4_

  - [x] 8.3 Modify `miniprogram/pages/order/detail/detail.js` to show demand/quote info and tracking number input
    - Load and display demand info and quote info sections
    - Add tracking number input when supplier transitions to "shipped"
    - Allow admin to view order detail (read-only)
    - _Requirements: 3.1, 3.2, 4.3_

  - [x] 8.4 Modify `miniprogram/pages/order/detail/detail.wxml` to add demand/quote sections and tracking input
    - Add demand info section card (title, quantity, composition)
    - Add quote info section card (price, delivery days, message)
    - Add tracking number input in the shipped confirmation modal
    - Show tracking number in order info when available
    - _Requirements: 3.1, 4.3_

  - [x] 8.5 Update `miniprogram/pages/order/detail/detail.wxss` for new sections styling
    - Style demand info and quote info cards
    - Style tracking number input field
    - _Requirements: 3.1_

- [x] 9. Checkpoint - Frontend order flow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Update message page with conversation tab and create chat detail page
  - [x] 10.1 Modify `miniprogram/pages/message/message.js` to add dual-tab layout (conversations + notifications)
    - Add `activeTab` state ('conversations' / 'notifications')
    - Add `conversationList` data and loading methods calling `GET /api/conversations`
    - Add `_loadConversations` method with pagination
    - Add `_loadUnreadConvCount` method calling `GET /api/conversations/unread-count`
    - Keep existing notification loading logic for the notifications tab
    - Add `onConversationTap` to navigate to chat detail page
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 10.2 Modify `miniprogram/pages/message/message.wxml` for dual-tab layout
    - Add tab bar at top: 会话 / 通知
    - Conversation tab: show conversation list with counterparty name, demand title, last message preview, time, unread badge
    - Notification tab: keep existing message list layout
    - _Requirements: 8.1, 8.2_

  - [x] 10.3 Update `miniprogram/pages/message/message.wxss` for tab styling and conversation cards
    - Style tab bar with macaron color scheme
    - Style conversation list cards with unread indicator
    - _Requirements: 8.1, 8.2_

  - [x] 10.4 Create chat detail page `miniprogram/pages/message/chat/chat.js`
    - Load conversation messages via `GET /api/conversations/:id/messages`
    - Implement send message via `POST /api/conversations/:id/messages`
    - Implement pull-down to load older messages (pagination)
    - Auto-scroll to bottom on new messages
    - Display system messages with distinct styling
    - Show conversation header with counterparty name and demand title
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 10.5 Create chat detail page `miniprogram/pages/message/chat/chat.wxml`
    - Chat bubble layout: own messages on right (macaron pink), other's on left (macaron blue)
    - System messages centered with muted styling
    - Bottom input bar with text input and send button
    - Loading indicator for older messages
    - _Requirements: 7.1, 7.3_

  - [x] 10.6 Create chat detail page `miniprogram/pages/message/chat/chat.wxss`
    - Style chat bubbles, input bar, system messages
    - Macaron/pastel color scheme consistent with existing pages
    - _Requirements: 7.1_

  - [x] 10.7 Create chat detail page `miniprogram/pages/message/chat/chat.json`
    - Configure page with navigation bar title "聊天"
    - Register any needed components
    - _Requirements: 7.1_

  - [x] 10.8 Register chat page route in `miniprogram/app.json`
    - Add `pages/message/chat/chat` to the pages array
    - _Requirements: 8.3_

- [x] 11. Update admin page for order and conversation monitoring
  - [x] 11.1 Modify `miniprogram/pages/admin/admin.js` to add order and conversation monitoring sections
    - Add methods to load all orders and all conversations via existing APIs (admin role returns all)
    - Add navigation to order detail and conversation chat pages
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 11.2 Modify `miniprogram/pages/admin/admin.wxml` to display order and conversation monitoring UI
    - Add order monitoring section with order list cards
    - Add conversation monitoring section with conversation list
    - _Requirements: 9.1, 9.3_

  - [x] 11.3 Update `miniprogram/pages/admin/admin.wxss` for monitoring section styling
    - Style monitoring cards consistent with macaron theme
    - _Requirements: 9.1_

- [x] 12. Final checkpoint - Full integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use Hypothesis library with minimum 100 iterations
- Backend tasks (1-6) should be completed before frontend tasks (7-11)
- Existing Order creation flow via fabric items is preserved (backward compatible)
- All user-facing text in Chinese, macaron/pastel color scheme
