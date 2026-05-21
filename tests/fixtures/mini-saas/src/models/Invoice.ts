import { Entity, Column, PrimaryGeneratedColumn, ManyToOne } from "typeorm";
import { User } from "./User";

@Entity()
export class Invoice {
  @PrimaryGeneratedColumn()
  id!: number;

  @ManyToOne(() => User)
  user!: User;

  @Column("decimal")
  amount!: number;

  @Column({ default: "open" })
  status!: string;

  @Column({ type: "date" })
  due_date!: string;
}
