# Requirements Document

## Introduction

本需求文档描述纺织面料智能查询与供需对接平台的两项核心增强功能：（1）报价转订单流程——当采购方接受供应商报价后自动创建订单，并支持完整的订单生命周期管理；（2）会话聊天系统——当供应商对需求提交报价时自动创建双方会话，支持实时消息交流，管理员可监控所有会话。

## Glossary

- **Platform**: 纺织面料智能查询与供需对接平台的后端服务（Flask）和前端（微信小程序）
- **Buyer**: 角色为 buyer 的已认证用户，可发布采购需求、接受报价、确认收货
- **Supplier**: 角色为 supplier 的已认证用户，可对需求提交报价、确认订单、更新订单进度
- **Admin**: 角色为 admin 的管理员用户，可查看所有订单和会话进行监控
- **Demand**: 采购方发布的采购需求，包含面料参数和数量要求
- **Quote**: 供应商对某条 Demand 提交的报价，包含价格、交货天数和说明
- **Order**: 由接受报价动作自动创建的采购订单，关联 Demand 和 Quote
- **Conversation**: 围绕某条 Demand 在 Buyer 和 Supplier 之间建立的聊天会话
- **ChatMessage**: Conversation 中的单条聊天消息
- **Order_Status**: 订单状态枚举：pending → confirmed → producing → shipped → received → completed

## Requirements

### Requirement 1: 接受报价并自动创建订单

**User Story:** As a Buyer, I want to accept a supplier's quote on my demand, so that an order is automatically created linking the demand, quote, buyer, and supplier.

#### Acceptance Criteria

1. WHEN a Buyer accepts a Quote on a Demand, THE Platform SHALL set the Quote status to "accepted", set all other Quotes on the same Demand to "rejected", and set the Demand status to "closed"
2. WHEN a Quote is accepted, THE Platform SHALL create an Order with status "pending", linking the Buyer, Supplier, Demand, and Quote, using the Quote price and Demand quantity to calculate total_amount
3. WHEN a Quote is accepted, THE Platform SHALL send a notification to the Supplier informing them that their quote was accepted and an order was created
4. IF a Buyer attempts to accept a Quote on a Demand that is not in "open" status, THEN THE Platform SHALL reject the request and return an error message
5. IF a Buyer attempts to accept a Quote that does not belong to their own Demand, THEN THE Platform SHALL reject the request with a 403 error

### Requirement 2: 订单列表与角色过滤

**User Story:** As a Buyer or Supplier, I want to see only my own orders in the order list, so that I can track my transactions.

#### Acceptance Criteria

1. WHEN a Buyer requests the order list, THE Platform SHALL return only Orders where the Buyer is the buyer_id, ordered by creation time descending
2. WHEN a Supplier requests the order list, THE Platform SHALL return only Orders where the Supplier is the supplier_id, ordered by creation time descending
3. WHEN an Admin requests the order list, THE Platform SHALL return all Orders, ordered by creation time descending
4. THE Platform SHALL include demand title, quote price, and counterparty company name in each order list item

### Requirement 3: 订单详情展示

**User Story:** As a Buyer or Supplier, I want to view the full details of an order, so that I can see the linked demand, quote, and status timeline.

#### Acceptance Criteria

1. WHEN a Buyer or Supplier views an Order detail, THE Platform SHALL display the order number, status, total amount, demand title, quote details, buyer info, supplier info, and status timeline
2. WHEN an Admin views an Order detail, THE Platform SHALL display the same information as Buyer/Supplier
3. THE Platform SHALL display a status timeline showing all six statuses with the current status highlighted
4. IF a user who is not the Buyer, Supplier, or Admin attempts to view an Order, THEN THE Platform SHALL return a 403 error

### Requirement 4: 供应商更新订单进度

**User Story:** As a Supplier, I want to update order progress through the status flow, so that the buyer can track the order lifecycle.

#### Acceptance Criteria

1. WHEN a Supplier confirms an Order, THE Platform SHALL transition the Order status from "pending" to "confirmed"
2. WHEN a Supplier marks an Order as producing, THE Platform SHALL transition the Order status from "confirmed" to "producing"
3. WHEN a Supplier marks an Order as shipped, THE Platform SHALL transition the Order status from "producing" to "shipped" and store the tracking number
4. WHEN the Order status changes, THE Platform SHALL send a notification to the Buyer with the new status
5. IF a Supplier attempts a status transition that violates the sequential order, THEN THE Platform SHALL reject the request and return an error message

### Requirement 5: 采购方确认收货与完成

**User Story:** As a Buyer, I want to confirm receipt and mark the order as completed, so that the transaction lifecycle is finalized.

#### Acceptance Criteria

1. WHEN a Buyer confirms receipt of a shipped Order, THE Platform SHALL transition the Order status from "shipped" to "received"
2. WHEN a Buyer marks a received Order as completed, THE Platform SHALL transition the Order status from "received" to "completed"
3. WHEN the Buyer updates the Order status, THE Platform SHALL send a notification to the Supplier with the new status
4. IF a Buyer attempts to confirm receipt on an Order that is not in "shipped" status, THEN THE Platform SHALL reject the request

### Requirement 6: 报价提交时自动创建会话

**User Story:** As a Supplier, I want a conversation to be automatically created when I submit a quote, so that I can communicate with the buyer about the demand.

#### Acceptance Criteria

1. WHEN a Supplier submits a Quote on a Demand, THE Platform SHALL create a Conversation between the Supplier and the Demand's Buyer, linked to that Demand
2. WHEN a Conversation already exists between the same Supplier and Buyer for the same Demand, THE Platform SHALL reuse the existing Conversation instead of creating a duplicate
3. WHEN a Conversation is created, THE Platform SHALL generate an initial system ChatMessage summarizing the quote details (price, delivery days)

### Requirement 7: 会话内消息收发

**User Story:** As a Buyer or Supplier, I want to send and receive messages within a conversation, so that I can discuss demand details and negotiate.

#### Acceptance Criteria

1. WHEN a user sends a ChatMessage in a Conversation, THE Platform SHALL store the message with sender ID, content, and timestamp
2. WHEN a ChatMessage is sent, THE Platform SHALL update the Conversation's last_message_at timestamp and last_message_preview text
3. WHEN a user opens a Conversation, THE Platform SHALL return all ChatMessages in chronological order with pagination support
4. WHEN a user opens a Conversation, THE Platform SHALL mark all unread ChatMessages from the other party as read
5. IF a user who is not a participant of the Conversation (and not Admin) sends a message, THEN THE Platform SHALL reject the request with a 403 error

### Requirement 8: 会话列表展示

**User Story:** As a Buyer or Supplier, I want to see my conversation list on the message page, so that I can quickly find and continue discussions.

#### Acceptance Criteria

1. WHEN a Buyer or Supplier opens the message page, THE Platform SHALL display a list of their Conversations ordered by last_message_at descending
2. THE Platform SHALL display the counterparty company name, demand title, last message preview, last message time, and unread message count for each Conversation
3. WHEN a user taps a Conversation, THE Platform SHALL navigate to the chat detail page for that Conversation
4. THE Platform SHALL display the total unread conversation message count as a badge on the message tab

### Requirement 9: 管理员监控

**User Story:** As an Admin, I want to view all orders and conversations, so that I can monitor platform activity and resolve disputes.

#### Acceptance Criteria

1. WHEN an Admin requests the conversation list, THE Platform SHALL return all Conversations across all users
2. WHEN an Admin opens a Conversation, THE Platform SHALL display all ChatMessages in read-only mode
3. WHEN an Admin views the order list, THE Platform SHALL return all Orders with buyer and supplier information
