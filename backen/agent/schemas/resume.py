from pydantic import BaseModel, Field
from typing import List, Optional


class Skill(BaseModel):
    name: str = Field(description="技能名称，如 Java、Spring Boot")
    level: str = Field(description="熟练度，如 精通/熟练/了解")


class Certificate(BaseModel):
    name: str = Field(description="证书名称，如 英语四级、软考中级")


class Internship(BaseModel):
    company: str = Field(description="实习公司")
    role: str = Field(description="实习岗位")
    duration: str = Field(description="实习时长")
    description: str = Field(description="实习内容简述")


class ResumeProfile(BaseModel):
    """学生能力画像（简历解析结果，7 维度）"""
    name: Optional[str] = Field(None, description="姓名")
    school: Optional[str] = Field(None, description="院校")
    major: Optional[str] = Field(None, description="专业")
    education: Optional[str] = Field(None, description="学历")
    skills: List[Skill] = Field(default_factory=list, description="专业技能")
    certificates: List[Certificate] = Field(default_factory=list, description="证书")
    project_experience: str = Field("", description="项目经验描述（项目名称、技术栈、职责、成果，多段合并）")
    innovation: str = Field("", description="创新能力描述")
    learning_ability: str = Field("", description="学习能力描述")
    pressure_ability: str = Field("", description="抗压能力描述")
    communication: str = Field("", description="沟通能力描述")
    internships: List[Internship] = Field(default_factory=list, description="实习经历")
