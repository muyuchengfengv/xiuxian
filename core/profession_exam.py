"""
职业考核系统
管理职业品级考核和晋升
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import random
import json
from astrbot.api import logger

from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..core.profession import ProfessionManager, ProfessionNotFoundError


class ExamError(Exception):
    """考核系统异常"""
    pass


class ExamNotAvailableError(ExamError):
    """考核不可用"""
    pass


class InsufficientSpiritStoneError(ExamError):
    """灵石不足"""
    pass


class ProfessionExamManager:
    """职业考核管理器"""

    # 考核配置
    EXAM_REQUIREMENTS = {
        # 炼丹师考核
        "alchemist": {
            2: {  # 升到2品的考核
                "title": "二品炼丹师考核",
                "description": "炼制指定丹药,回答炼丹知识问题",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "回血丹",
                        "quality_min": "中品",
                        "quantity": 3,
                        "description": "炼制3颗中品以上回血丹"
                    },
                    {
                        "type": "knowledge",
                        "question": "火候控制是炼丹的关键,请问文火和武火的主要区别是什么?",
                        "answers": ["文火温养药性,武火提炼精华", "文火慢炼,武火快炼", "文火适合炼药,武火适合炼器"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 500,
                    "reputation": 100
                },
                "cost_spirit_stone": 500
            },
            3: {
                "title": "三品炼丹师考核",
                "description": "炼制高品质丹药,展现丹道理解",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "筑基丹",
                        "quality_min": "中品",
                        "quantity": 2,
                        "description": "炼制2颗中品以上筑基丹"
                    },
                    {
                        "type": "knowledge",
                        "question": "灵根与炼丹的关系中,哪种灵根最适合炼丹?",
                        "answers": ["火系灵根", "木系灵根", "水系灵根", "金系灵根"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 1000,
                    "reputation": 200
                },
                "cost_spirit_stone": 1000
            }
        },
        # 炼器师考核
        "blacksmith": {
            2: {
                "title": "二品炼器师考核",
                "description": "炼制指定装备,回答炼器知识问题",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "玄铁剑",
                        "quality_min": "灵品",
                        "quantity": 2,
                        "description": "炼制2件灵品以上玄铁剑"
                    },
                    {
                        "type": "knowledge",
                        "question": "淬火是炼器的关键步骤,请问淬火的主要作用是什么?",
                        "answers": ["增加装备韧性和硬度", "增加装备重量", "使装备冷却", "使装备发光"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 500,
                    "reputation": 100
                },
                "cost_spirit_stone": 500
            },
            3: {
                "title": "三品炼器师考核",
                "description": "炼制高品质装备,展现炼器技艺",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "聚灵戒指",
                        "quality_min": "宝品",
                        "quantity": 1,
                        "description": "炼制1件宝品以上聚灵戒指"
                    },
                    {
                        "type": "knowledge",
                        "question": "在炼器过程中,哪种灵根最适合炼器?",
                        "answers": ["金系灵根", "火系灵根", "土系灵根", "水系灵根"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 1000,
                    "reputation": 200
                },
                "cost_spirit_stone": 1000
            }
        },
        # 阵法师考核
        "formation_master": {
            2: {
                "title": "二品阵法师考核",
                "description": "布置指定阵法,回答阵法知识问题",
                "tasks": [
                    {
                        "type": "deploy",
                        "target": "聚灵阵",
                        "success_count": 2,
                        "description": "成功布置2次聚灵阵"
                    },
                    {
                        "type": "knowledge",
                        "question": "阵法的阵眼是什么?",
                        "answers": ["阵法的核心枢纽", "阵法的入口", "阵法的出口", "阵法的边界"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 500,
                    "reputation": 100
                },
                "cost_spirit_stone": 500
            },
            3: {
                "title": "三品阵法师考核",
                "description": "布置复杂阵法,展现阵道修为",
                "tasks": [
                    {
                        "type": "deploy",
                        "target": "五行杀阵",
                        "success_count": 1,
                        "description": "成功布置1次五行杀阵"
                    },
                    {
                        "type": "knowledge",
                        "question": "五行阵法的相生顺序是什么?",
                        "answers": ["金生水,水生木,木生火,火生土,土生金", "木生火,火生土,土生金,金生水,水生木", "土生金,金生水,水生木,木生火,火生土"],
                        "correct_index": 1
                    }
                ],
                "rewards": {
                    "experience": 1000,
                    "reputation": 200
                },
                "cost_spirit_stone": 1000
            }
        },
        # 符箓师考核
        "talisman_master": {
            2: {
                "title": "二品符箓师考核",
                "description": "制作指定符箓,回答符箓知识问题",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "火球符",
                        "quantity": 5,
                        "description": "成功制作5张火球符"
                    },
                    {
                        "type": "knowledge",
                        "question": "符箓制作中,符墨的主要成分是什么?",
                        "answers": ["朱砂和灵兽血", "墨汁和灵石粉", "朱砂和墨汁", "灵兽血和灵液"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 500,
                    "reputation": 100
                },
                "cost_spirit_stone": 500
            },
            3: {
                "title": "三品符箓师考核",
                "description": "制作高级符箓,展现符道造诣",
                "tasks": [
                    {
                        "type": "craft",
                        "target": "五雷符",
                        "quantity": 2,
                        "description": "成功制作2张五雷符"
                    },
                    {
                        "type": "knowledge",
                        "question": "符箓的灵力注入需要注意什么?",
                        "answers": ["灵力均匀稳定注入", "灵力越多越好", "灵力越快越好", "灵力不重要"],
                        "correct_index": 0
                    }
                ],
                "rewards": {
                    "experience": 1000,
                    "reputation": 200
                },
                "cost_spirit_stone": 1000
            }
        }
    }

    def __init__(
        self,
        db: DatabaseManager,
        player_mgr: PlayerManager,
        profession_mgr: ProfessionManager
    ):
        """
        初始化职业考核管理器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr

    async def start_exam(
        self,
        user_id: str,
        profession_type: str
    ) -> Dict[str, Any]:
        """
        开始职业考核

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            Dict: 考核信息

        Raises:
            ProfessionNotFoundError: 职业不存在
            ExamNotAvailableError: 考核不可用
            InsufficientSpiritStoneError: 灵石不足
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 检查是否可以升品
        if not profession.check_rank_upgrade():
            raise ExamNotAvailableError(
                f"尚未满足升品条件,需要Lv.10以上且声望达到{profession.rank * 1000}"
            )

        # 获取考核配置
        target_rank = profession.rank + 1
        if profession_type not in self.EXAM_REQUIREMENTS:
            raise ExamNotAvailableError(f"职业{profession_type}没有考核配置")

        exam_config = self.EXAM_REQUIREMENTS[profession_type].get(target_rank)
        if not exam_config:
            raise ExamNotAvailableError(f"没有{target_rank}品的考核配置")

        # 检查灵石
        cost = exam_config['cost_spirit_stone']
        player = await self.player_mgr.get_player_or_error(user_id)
        if player.spirit_stone < cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{cost}灵石")

        # 扣除灵石
        await self.player_mgr.add_spirit_stone(user_id, -cost)

        # 创建考核记录
        await self.db.execute(
            """
            INSERT INTO profession_exams (
                user_id, profession_type, target_rank, exam_title,
                tasks, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                profession_type,
                target_rank,
                exam_config['title'],
                json.dumps(exam_config['tasks']),
                'in_progress',
                datetime.now().isoformat()
            )
        )

        logger.info(f"玩家 {user_id} 开始{exam_config['title']}")

        return {
            'exam_title': exam_config['title'],
            'description': exam_config['description'],
            'tasks': exam_config['tasks'],
            'cost': cost,
            'message': f"考核已开始: {exam_config['title']}\n请完成以下任务:"
        }

    async def answer_question(
        self,
        user_id: str,
        profession_type: str,
        task_index: int,
        answer_index: int
    ) -> Dict[str, Any]:
        """
        回答考核问题

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            task_index: 任务索引
            answer_index: 答案索引

        Returns:
            Dict: 回答结果
        """
        # 获取当前考核
        exam = await self._get_current_exam(user_id, profession_type)
        if not exam:
            raise ExamError("没有进行中的考核")

        # 解析任务
        tasks = json.loads(exam['tasks'])
        if task_index >= len(tasks):
            raise ExamError("任务索引无效")

        task = tasks[task_index]
        if task['type'] != 'knowledge':
            raise ExamError("该任务不是知识问答")

        # 检查答案
        correct = answer_index == task['correct_index']

        return {
            'correct': correct,
            'correct_answer': task['answers'][task['correct_index']],
            'your_answer': task['answers'][answer_index] if answer_index < len(task['answers']) else "无效答案",
            'message': "回答正确!" if correct else f"回答错误!正确答案是: {task['answers'][task['correct_index']]}"
        }

    async def submit_exam(
        self,
        user_id: str,
        profession_type: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提交考核结果

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            results: 考核结果 {"task_0": True/False, "task_1": True/False, ...}

        Returns:
            Dict: 考核结果
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 获取当前考核
        exam = await self._get_current_exam(user_id, profession_type)
        if not exam:
            raise ExamError("没有进行中的考核")

        # 解析任务
        tasks = json.loads(exam['tasks'])

        # 计算通过率
        total_tasks = len(tasks)
        passed_tasks = sum(1 for result in results.values() if result)
        pass_rate = passed_tasks / total_tasks if total_tasks > 0 else 0

        # 判断是否通过(需要全部任务通过)
        passed = pass_rate >= 1.0

        # 更新考核记录
        status = 'passed' if passed else 'failed'
        await self.db.execute(
            """
            UPDATE profession_exams
            SET status = ?, results = ?, completed_at = ?
            WHERE user_id = ? AND profession_type = ? AND status = 'in_progress'
            """,
            (
                status,
                json.dumps(results),
                datetime.now().isoformat(),
                user_id,
                profession_type
            )
        )

        if passed:
            # 考核通过,升品
            target_rank = exam['target_rank']
            exam_config = self.EXAM_REQUIREMENTS[profession_type][target_rank]

            # 升品
            await self.profession_mgr.upgrade_rank(user_id, profession_type)

            # 奖励经验和声望
            exp_reward = exam_config['rewards']['experience']
            rep_reward = exam_config['rewards']['reputation']

            await self.profession_mgr.add_experience(user_id, profession_type, exp_reward)
            await self.profession_mgr.add_reputation(user_id, profession_type, rep_reward)

            logger.info(f"玩家 {user_id} 通过{exam['exam_title']},升至{target_rank}品")

            return {
                'passed': True,
                'new_rank': target_rank,
                'experience_reward': exp_reward,
                'reputation_reward': rep_reward,
                'message': f"恭喜!考核通过!晋升为{target_rank}品{profession.get_profession_name()}!"
            }
        else:
            logger.info(f"玩家 {user_id} 未通过{exam['exam_title']}")

            return {
                'passed': False,
                'passed_tasks': passed_tasks,
                'total_tasks': total_tasks,
                'message': f"考核未通过({passed_tasks}/{total_tasks}),请继续努力!"
            }

    async def get_exam_info(
        self,
        user_id: str,
        profession_type: str
    ) -> Dict[str, Any]:
        """
        获取考核信息

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            Dict: 考核信息
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 获取当前考核
        exam = await self._get_current_exam(user_id, profession_type)

        if exam:
            tasks = json.loads(exam['tasks'])
            return {
                'in_progress': True,
                'exam_title': exam['exam_title'],
                'target_rank': exam['target_rank'],
                'tasks': tasks,
                'started_at': exam['created_at']
            }
        else:
            # 检查是否可以开始新考核
            can_exam = profession.check_rank_upgrade()
            if can_exam:
                target_rank = profession.rank + 1
                exam_config = self.EXAM_REQUIREMENTS.get(profession_type, {}).get(target_rank)
                if exam_config:
                    return {
                        'in_progress': False,
                        'can_start': True,
                        'next_exam': exam_config,
                        'target_rank': target_rank,
                        'cost': exam_config['cost_spirit_stone']
                    }

            return {
                'in_progress': False,
                'can_start': False,
                'message': f"尚未满足升品条件,需要Lv.10以上且声望达到{profession.rank * 1000}"
            }

    async def _get_current_exam(
        self,
        user_id: str,
        profession_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取当前进行中的考核"""
        row = await self.db.fetchone(
            """
            SELECT * FROM profession_exams
            WHERE user_id = ? AND profession_type = ? AND status = 'in_progress'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, profession_type)
        )
        return dict(row) if row else None

    async def _create_exam_table(self):
        """创建考核记录表(如果不存在)"""
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS profession_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                target_rank INTEGER NOT NULL,
                exam_title TEXT NOT NULL,
                tasks TEXT,
                results TEXT,
                status TEXT DEFAULT 'in_progress',
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
            """
        )
        logger.info("职业考核表创建完成")
